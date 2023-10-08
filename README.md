# Lib2OPDS

`lib2opds` generates OPDS catalog for local e-book library so it can be hosted utilizing web server. Currently meta data extraction is supported only for ePUB format.

## How to install

1. Clone the repository
2. Run `poetry install`

## How to use

```
$ tree ./test-library/
./test-library/
├── Linux
│   └── How Linux Works - Brian Ward.epub
└── Science Fiction
    ├── All Systems Red.epub
    └── I, Robot - Isaac Asimov.epub

$ poetry run lib2opds --opds-base-uri "/opds/" --library-base-uri "/library/" --library-dir "./test-library" --opds-dir "./output"

$ tree ./output/
./output/
├── covers
│   ├── 607b2fca-05f3-4ec3-9f6f-d2102b30280e
│   └── 9a3ef480-41e2-4425-a2cc-61cf5bfedda4
├── index.xml
├── Linux
│   └── index.xml
└── Science Fiction
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
