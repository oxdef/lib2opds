# Lib2OPDS

`lib2opds` generates static [OPDS](https://opds.io/) ([version 1.2](https://specs.opds.io/opds-1.2)) catalog for local e-book library.

## Features

- Directory hierarchy support
- Virtual directories: new books, authors, etc.
- ePUB format: metadata extraction, thumbnail generation
- PDF format: metadata extraction, thumbnail generation
- "Lazy" updating of feeds. `lib2opds` re-generates feeds only when new files are added into the library
- Sidecar files for metadata extraction
- Global and local configuration files as well as command line options
- Caching for better processing of libraries with many books
- Static site generation

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

$ lib2opds --opds-base-uri "/opds/" --library-base-uri "/library/" --library-dir "./test-library" --opds-dir "./output" --generate-site

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
├── pages
│   ├── 101bcb13-37bf-4e13-a543-22c5ff3567d3.html
│   ├── 127ae484-af53-4056-9cff-517984321e26.html
│   └── db1d5760-72f5-4f23-af42-d9d6406207c9.html
├── index.html
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
        index index.xml;
}

location /opds/covers {
        alias /opds-dir/covers;
}
```

Library location here is not protected with basic auth because of the bug in some e-book reader software.

## Sidecar files

`lib2opds` detects sidecar files for the target e-book file and extracts metadata and cover from them.

For example, in case of `some-book.epub` e-book file `lib2opds` will try to check for `some-book.info` and `some-book.cover` files.

`.info` sidecar files are basically INI-format files:

```
[Publication]
title = 1984
authors =  George Orwell
description = Some summary here
language = en
issued = 1949
publisher = SomePublisher, Inc.
identifier = urn:isbn:9781443434973
```

`.cover` is just an image file.

## Tested devices and applications

The full list of devices and applications is available on [the wiki page](https://github.com/oxdef/lib2opds/wiki/Tested-devices-and-applications).
