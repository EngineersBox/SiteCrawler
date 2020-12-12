# SiteCrawler

A website crawler that rescursively explores links on the page. External to depth 1 and internal to depth n

- [SiteCrawler](#sitecrawler)
  - [Requirements](#requirements)
  - [Setup](#setup)
    - [Windows](#windows)
    - [Unix](#unix)
  - [Running the Script](#running-the-script)
  - [Acknowledgements](#acknowledgements)

## Requirements

- **Dependencies** (included in requirements.txt - see below)
  - bs4
  - requests
  - lxml
  
- **Python Versions Tested**
  - 3.8.2 - 3.9

---

## Setup

### Windows

```cmd
python3 -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

*or*

```cmd
make setup_win
```

### Unix

```cmd
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

*or*

```cmd
make setup_unix
```

## Running the Script

```cmd
python3 map_website.py -d https://webscrapethissite.org -o test.txt
```

---

## Acknowledgements

This is based on an implementation by Ahad Sheriff with the following license:

> Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
> 
> The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
>
> THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
