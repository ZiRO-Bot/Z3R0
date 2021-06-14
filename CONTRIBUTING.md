# Contributing to this repository
Please try to follow these guidelines when contributing/making pull requests to this repository
- To contribute, fork the repo, edit the fork, and create a pull requests.
- Naming guidelines:
  * Classes: `CamelCase`
  * Functions: `lowerCamelCase`
  * Variables **inside** a function/class: `lowerCamelCase`
  * Variables **outside** a function/class: `UPPERCASE`
- All database query should be stored in `exts/utils/dbQuery.py` unless the query guaranteed to work in SQLite3, PostgreSQL, and MySQL.
- Use `str.format()` instead of f-string unless there's no words in it (For i18n, maybe in the future)
- Format your code with [`black`](https://github.com/psf/black) before creating a pull request.
