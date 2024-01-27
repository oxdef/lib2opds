# Lib2OPDS

`lib2opds` generates [OPDS](https://opds.io/) ([version 1.2](https://specs.opds.io/opds-1.2)) catalog for local e-book library so it can be hosted utilizing web server. Currently meta data extraction is supported only for ePUB format.

## Features

- Directory hierarchy support
- Virtual directories: new books, authors, etc.
- ePUB format: metadata extraction, thumbnail generation
- PDF format: metadata extraction, thumbnail generation
- "Lazy" updating of feeds. `lib2opds` re-generates feeds only when new files are added into the library
- Sidecar files for metadata extraction
- Global and local configuration files as well as command line options
- Caching for better processing of libraries with many books

## How to install

`lib2opds` is distributed on PyPI. The best way to install it is with [pipx](https://pipx.pypa.io).

```
pipx install lib2opds
```

## How to use

```
$ tree ./test-library/
./test-library/
├── Linux
│   └── How Linux Works - Brian Ward.epub
└── Science Fiction
    ├── All Systems Red.epub
    └── I, Robot - Isaac Asimov.epub

$ lib2opds --opds-base-uri "/opds/" --library-base-uri "/library/" --library-dir "./test-library" --opds-dir "./output"

$ tree ./output/
./output/

├── covers
│   ├── 03e1b3fe-66b2-43eb-b9f1-da72813419e2
│   ├── 14cdd72c-680c-491c-a017-ddd0d2dbb1d2
│   └── e01dab66-3f78-402a-9ac8-83ebc6b24f11
├── feeds
│   ├── 101bcb13-37bf-4e13-a543-22c5ff3567d3.xml
│   ├── 127ae484-af53-4056-9cff-517984321e26.xml
│   └── db1d5760-72f5-4f23-af42-d9d6406207c9.xml
└── index.xml
```

`/etc/lib2opds.ini` is used by default and options can be overridden via command line arguments.

Example of configuration file for Nginx:

```nginx
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

## Tested devices and applications

* PocketBook devices
* KyBook 3 EBook Reader
