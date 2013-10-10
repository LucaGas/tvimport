This is a python daemon to rename, order and rearrange tv series files. It watches a directory thanks to inotify and if any file is added to that directory the daemon tries to extract some information from it(title, season, 
episode). With this information the daemon queries the tvdb database for the title of the episode. Finally the file is moved to its destination (ex Lost/Season 1/Lost.S01E01.Pilot.mkv).

## Requirement
An inotify enabled kernel ( I guess this means linux only)
Python modules:
* tvdb_api
* pyinotify

## Installation
```pip install tvimport```

## Usage

``` tvimport start source_dir dest_dir```

source_dir: the directory where you will move the files that need to be renamed
dest_dir: the directory where you want to move the files to. For example if dest_dir is /media/Downloads the final destination will be /media/Downloads/Lost/Season 1/Lost.S01E01.Pilot.mkv

   
