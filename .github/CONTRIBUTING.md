# Contributing to this repository
Please try to follow these guidelines when contributing/making pull requests to this repository
- To contribute, fork the repo, edit the fork, and create a pull requests.
- Naming guidelines:
  * Classes: `CamelCase`
  * Functions: `snake_case` or `lowerCamelCase` (Always use `lowerCamelCase` if possible)
  * Variables **inside** a function/class: `lowerCamelCase`
  * Variables **outside** a function/class: `UPPERCASE`
- New functions should include informative docstring/comments.
- Use `str.format()` instead of f-string unless there's no words in it (For i18n, maybe in the future)
- Format your code with [`black`](https://github.com/psf/black) before creating a pull request.
