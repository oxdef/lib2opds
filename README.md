# Lib2OPDS

`lib2opds` generates OPDS catalog for local e-book library so it can be hosted utilizing web server. Currently meta data extraction is supported only for ePUB format.

## How to install

1. Clone the repository
2. Run `poetry install`

## How to use

```
$ poetry run lib2opds -h

usage: lib2opds [-h] [--library-dir LIBRARY_DIR] [--opds-dir OPDS_DIR] [--library-base-uri LIBRARY_BASE_URI] [--opds-base-uri OPDS_BASE_URI]
                [--library_title LIBRARY_TITLE] [-c CONFIG]

Generate OPDS catalog for local e-book library

options:
  -h, --help            show this help message and exit
  --library-dir LIBRARY_DIR
                        Directory with your books
  --opds-dir OPDS_DIR   Target directory for OPDS feeds
  --library-base-uri LIBRARY_BASE_URI
                        Base URI for serving books from the library, for example https://your-domain.com/library
  --opds-base-uri OPDS_BASE_URI
                        Base URI for OPDS, for example https://your-domain.com/opds
  --library_title LIBRARY_TITLE
                        Lybrary title
  -c CONFIG, --config CONFIG
                        Config path
```

`/etc/lib2opds.ini` is used by default and options can be overridden via command line arguments.

Example of configuration file for Nginx:

```
location /library {
        alias /library-dir;
}

location /opds {
        auth_basic  "Library Area";
        auth_basic_user_file /etc/nginx/htpasswd;
        alias /opds-dir;
        index root.xml index.xml;
}

location /opds/covers {
        alias /opds-dir/covers;
}
```

Library location here is not protected with basic auth because of the bug in some e-book reader software.
