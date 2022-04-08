# CSS coverage generator

Useful script to analyze and visualize used css code  
Collects line coverage statistics and generates coverage report in html file

# Installation

Make sure you have `python3` installed on your computer

# Usage

## Generate a Coverage report:

- Open Chrome Dev Tools
- In the Console panel click the three dots and `Coverage`
- Record
- Export
- Repeat for as much website pages as needed
- Put generated `json`'s to folder with this script
- Additionaly you may put sourcemaps for your css files
- Run
```
python3 script.py
```
- A handful of files with `.cov.html` extension is generated, just open them in your browser

# Credits

Credit for base64 VLQ decoder to @mjpieters

# License

[MIT](https://github.com/daniilzinevich/css-coverage/blob/main/LICENSE)
