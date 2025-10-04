# Lib2OPDS

`lib2opds` generates static [OPDS](https://opds.io/) ([version 1.2](https://specs.opds.io/opds-1.2)) catalog for local e-book library.

## Features

- Directory hierarchy support
- Virtual directories: new books, authors, languages, decade issued, etc.
- ePUB format: metadata extraction, thumbnail generation
- PDF format: metadata extraction, thumbnail generation
- "Lazy" updating of feeds. `lib2opds` re-generates feeds only when new files are added into the library
- Sidecar files for metadata extraction
- Global and local configuration files as well as command line options
- Caching for better processing of libraries with many books
- Static site generation: with additional HTML file per feed or with client-side XSLT processing for the feed XML files (like for RSS/Atom feeds)

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

$ lib2opds --opds-base-uri "/opds/" --library-base-uri "/library/" --library-dir "./test-library" --opds-dir "./output" --generate-site-xslt

$ tree ./output/
./output/

├── assets
│   ├── acquisition-feed.xsl
│   ├── navigation-feed.xsl
│   └── style.css
├── covers
│   ├── a965b65e-85f9-4e98-a02b-4ff316869a2c.jpg
│   └── d738ea6d-f205-45e6-b09d-17d9b95c0286.jpg
├── feeds
│   ├── 142ccd52-436c-402f-8094-524fb20af9d3.xml
│   ├── 414562bf-c592-47f3-a94d-b01120ee22ca.xml
│   ├── 44d48843-196b-409b-9bd9-67d928505121.xml
...
│   └── fab6423d-a3ea-4027-8d84-b372fbef4503.xml
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

## Dependenices

Thanks the following projects used in Lib2OPDS:

* [Jinja2](https://palletsprojects.com/p/jinja/)
* [PyPDF](https://pypdf.readthedocs.io/en/latest/)
* [defusedxml](https://github.com/tiran/defusedxml)
* [Pillow](http://python-pillow.github.io/)
