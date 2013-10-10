#!/usr/bin/env python

DEBUG=False

import os,re,sys,atexit,time,logging
from signal import SIGTERM
try:
    import pyinotify
except:
    sys.exit("Aborted: You need the python module called pyinotify to run this daemon\n")
try:
    from tvdb_api import Tvdb
except:
    sys.exit("Aborted: You need the python module called tvdb_api to run this daemon\n")

logger = logging.getLogger("TVimportLog")
# Logging
if DEBUG == True:
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.INFO)

if not os.path.exists (os.path.expanduser("~/.tvimport")):
    os.makedirs (os.path.expanduser("~/.tvimport"))

formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
handler = logging.FileHandler(os.path.expanduser("~/.tvimport/tvimport.log"))
handler.setFormatter(formatter)
logger.addHandler(handler)
# End Logging


class Daemon():
        """
        A generic daemon class.

        Usage: subclass the Daemon class and override the run() method
        """
        def __init__(self, pidfile, stdin='/dev/null', stdout='/dev/stdout', stderr='/dev/stderr'):
                self.stdin = stdin
                self.stdout = stdout
                self.stderr = stderr
                self.pidfile = pidfile

        def daemonize(self):
                """
                do the UNIX double-fork magic, see Stevens' "Advanced
                Programming in the UNIX Environment" for details (ISBN 0201563177)
                http://www.erlenstar.demon.co.uk/unix/faq_2.html#SEC16
                """
                try:
                        pid = os.fork()
                        if pid > 0:
                                # exit first parent
                                sys.exit(0)
                except OSError, e:
                        sys.stderr.write("fork #1 failed: %d (%s)\n" % (e.errno, e.strerror))
                        sys.exit(1)

                # decouple from parent environment
                os.chdir("/")
                os.setsid()
                os.umask(0)

                # do second fork
                try:
                        pid = os.fork()
                        if pid > 0:
                                # exit from second parent
                                sys.exit(0)
                except OSError, e:
                        sys.stderr.write("fork #2 failed: %d (%s)\n" % (e.errno, e.strerror))
                        sys.exit(1)

                # redirect standard file descriptors
                sys.stdout.flush()
                sys.stderr.flush()
                si = file(self.stdin, 'r')
                so = file(self.stdout, 'a+')
                se = file(self.stderr, 'a+', 0)
                os.dup2(si.fileno(), sys.stdin.fileno())
                os.dup2(so.fileno(), sys.stdout.fileno())
                os.dup2(se.fileno(), sys.stderr.fileno())
                # write pidfile
                atexit.register(self.delpid)
                pid = str(os.getpid())
                file(self.pidfile,'w+').write("%s\n" % pid)
                time.sleep(3)

        def delpid(self):
                os.remove(self.pidfile)

        def start(self):
                """
                Start the daemon
                """
                # Check for a pidfile to see if the daemon already runs
                try:
                        pf = file(self.pidfile,'r')
                        pid = int(pf.read().strip())
                        pf.close()
                except IOError:
                        pid = None

                if pid:
                        message = "pidfile %s already exist. Daemon already running?\n"
                        sys.stderr.write(message % self.pidfile)
                        sys.exit(1)

                # Start the daemon
                logger.info("Start")
                logger.debug("Debug")
                self.daemonize()
                self.run()

        def stop(self):
                """
                Stop the daemon
                """
                # Get the pid from the pidfile
                try:
                        pf = file(self.pidfile,'r')
                        pid = int(pf.read().strip())
                        pf.close()
                except IOError:
                        pid = None

                if not pid:
                        message = "pidfile %s does not exist. Daemon not running?\n"
                        sys.stderr.write(message % self.pidfile)
                        return # not an error in a restart

                # Try killing the daemon process        
                try:
                        while 1:
                                os.kill(pid, SIGTERM)
                                time.sleep(0.1)
                except OSError, err:
                        err = str(err)
                        if err.find("No such process") > 0:
                                if os.path.exists(self.pidfile):
                                        os.remove(self.pidfile)
                        else:
                                print str(err)
                                sys.exit(1)
                finally:
                                logger.info("Stop")
                    
        def restart(self):
                """
                Restart the daemon
                """
                self.stop()
                self.start()

        def run(self):
                """
                You should override this method when you subclass Daemon. It will be called after the process has been
                daemonized by start() or restart().
                """
                # create watch manager 
                wm = pyinotify.WatchManager()
                # watched events
                #mask =pyinotify.ALL_EVENTS 
                mask = pyinotify.IN_ATTRIB |pyinotify.IN_MOVED_TO|pyinotify.ALL_EVENTS 
                # create notifier, pass manager and event handler            
                #notifier = pyinotify.Notifier(wm, EventHandler())
                # Start watching a path, rec doesn't seem to work
                #wdd = wm.add_watch(dir, mask, rec=True)
                #start the notifier loop
                #notifier.loop()
                #try:
                #    notifier.loop(daemonize=True)
                #except pyinotify.NotifierError, err:
                #    print >> sys.stderr, err
                #Threaded
                notifier = pyinotify.ThreadedNotifier(wm, EventHandler())
                notifier.start()
                wdd = wm.add_watch(src_dir, mask, rec=True)
                while True:
                    time.sleep(1)

                wm.rm_watch(wdd.values())

                notifier.stop()
                


class TVObject():
    """class for tv object"""
    def __init__(self,file):
        self.name = file
        self.clean_name = self.clean().replace(' ','.')
        self.ep_showname, self.ep_number, self.ep_season, self.name = self.tv_parser(self.clean())
        # If the the regexp works
        if self.ep_showname and self.ep_number and self.ep_season:
           self.dest_dir_episode=dst_dir+"/"+self.ep_showname+"/"+"Season "+str(self.ep_season)
           self.ep_title=self.get_title(self.ep_showname,self.ep_number,self.ep_season)        
           self.final_name=self.name.replace('^s^e','S'+str(self.ep_season).zfill(2)+'E'+str(self.ep_number).zfill(2)).replace(' ','.')
           if self.ep_title.replace('.','').lower() in self.final_name.replace('.','').lower():
               self.final_name=self.final_name
           else:
               results= os.path.splitext(self.final_name)
               extension = results[1]
               filename = results[0]
               self.final_name=filename+"."+self.ep_title+extension
        # If the the regexp doesn't work
        else:
           logger.info("Regexp: Failed to extract info from %s"  % (self.name))  
           self.dest_dir_episode=dst_dir+"/Failed-Import/"
           self.final_name=self.name

    def clean(self):
        """Replace underscores with spaces, capitalise words and remove
        brackets and anything inbetween them.
        """
        s = self.name
        file =  self.name
        opening_brackets = ['(', '[', '<', '{']
        closing_brackets = [')', ']', '>', '}']
        for i in range(len(opening_brackets)):
            b = opening_brackets[i]
            c = closing_brackets[i]

            while b in s:
                start = s.find(b)
                end = s.find(c) + 1

                s = re.sub(re.escape(s[start:end]), '', s)

        results = os.path.splitext(s)
        extension = results[1]
        s = results[0]

        s = s.replace('_', ' ')
        s = s.replace('.', ' ')
        s = s.strip()
        words = s.split(' ')
        s = ' '.join([w.capitalize() for w in words])
        s = s + extension
        s = re.sub('S\d+(e)\d+', self.fix_episode, s)

        return s

    def get_title(self,ep_showname,ep_number,ep_season):
        t=Tvdb()
        try:        
            return  t[ep_showname][ep_season][ep_number]['episodename'].replace(' ','.')
        except:        
            logger.info("TVDB lookup failed for %s Season %s Episode %s" % (ep_showname,ep_season,ep_number)) 
            return  ""

    def fix_episode(self,matchobj):
        """Used by the clean function to fix season capitalisation"""
        return matchobj.group(0).upper()

    def tv_parser(self,file):
        """Extract info from the file"""
        def tv_extractor(file):
            ep_season = int(results.groups()[0])
            ep_number = int(results.groups()[1])
            ep_showname = re.match('(.+?)\^s', file)
            ep_showname = ep_showname.groups()[0].strip(' .')
            ep_showname= os.path.basename(ep_showname)
            return (ep_showname, ep_number, ep_season, file)
    
        results = re.search(r'[s|S](\d+)[e|E](\d+)', file)
        if results:
            file = re.sub('[s|S](\d+)[e|E](\d+)', '^s^e', file)
            return tv_extractor(file)

        results = re.search(' (\d)(\d\d) ', file)
        if results:
            file = re.sub('\d\d\d', '^s^e', file)
            return tv_extractor(file)

        results = re.search('(\d+)[Xx](\d\d)', file)
        if results:
            file = re.sub('\d+[Xx]\d\d', '^s^e', file)
            return tv_extractor(file)


        return ('', '', '', file)



class EventHandler(pyinotify.ProcessEvent):
    
        def process_ALL_EVENTS(self, event):
            print event.pathname
        def process_IN_ATTRIB(self, event):
            if os.path.isdir(event.pathname) == False:
                results = re.search('.*\.aria2', event.name)
                if not results:
                    self.move(event.name,event.pathname)
            else:
                self.move_dir(event)
        def process_IN_MOVED_TO(self, event):
            if os.path.isdir(event.pathname) == False:
                results = re.search('.*\.aria2', event.name)
                if not results:
                    self.move(event.name,event.pathname)
        def move(self, name,src):
            tv=TVObject(name)
            dst=(tv.dest_dir_episode+"/"+tv.final_name).encode('utf-8')
            if not os.path.exists (tv.dest_dir_episode):
                os.makedirs (tv.dest_dir_episode)
                st = os.stat(dst_dir)
                my_dir=tv.dest_dir_episode
                while (my_dir != dst_dir):
                    os.system('chown "%s" "%s"' % (st.st_uid,my_dir))
                    my_dir= os.path.abspath(os.path.join(my_dir, os.path.pardir))
            os.system('mv "%s" "%s"' % (src,dst)) 
        def move_dir(self, event):
            for root, subFolders, files in os.walk(event.pathname):
                for file in files:
                    self.move(file,os.path.join(root,file))

def main():       
    daemon = Daemon(os.path.expanduser("~/.tvimport/tvimport.pid"))
    
    def print_usage():
        print "usage: %s start|restart source destination" % sys.argv[0]
        print "       %s stop" % sys.argv[0]
        print "       source and destination must be two directories" % sys.argv[0]
        sys.exit(2)
       
    if len(sys.argv) == 4 or len(sys.argv) == 2:
        if len(sys.argv) == 4:
            if os.path.isdir(sys.argv[2]) and os.path.isdir(sys.argv[3]):
                global src_dir
                global dst_dir
                src_dir=sys.argv[2].rstrip('\/')
                dst_dir=sys.argv[3].rstrip('\/')
            else:
                print_usage() 
            if 'start' == sys.argv[1]:
                daemon.start()
            elif 'restart' == sys.argv[1]:
                daemon.restart()
            else:
                print_usage()    
            sys.exit(0)
        elif len(sys.argv) == 2:
            if 'stop' == sys.argv[1]:
                daemon.stop()
            else:
                print_usage()
    else:
        print_usage()
if __name__ == "__main__":
    main()
    
