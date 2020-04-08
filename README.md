# eGela Scraper

A web scraper for the Moodle based alumni web [eGela](https://egela.ehu.eus), hosted by University of the Basque Country.

## Usage

Launch the scraper with the following command. In the first launch it will setup your environment downloading the dependencies needed.

```
./scrap.sh -o /path/to/output/folder
```

After that, you will be prompted your eGela credentials to gain access to the website. Those credentials won't be stored or even shared, they are discarded after the login success.

## Folder structure

This script downloads the contents of the different courses you are enroled into in the following structure:

```
outputFolder
+-- course1
|   +-- section1
|   |   +-- document1.pdf
|   |   +-- document2.docx
|   |   +-- folder.zip
|   +-- section2
|   |   +-- slides.pptx
|   |   +-- subsection1
|   |   |   +-- document1.pdf
|   |   |   +-- document2.odt
+-- course2
|   +-- section1
...
```

## File types

The file types that the scraper will look for are stored in [fileTypes.txt](res/fileTypes.txt) file. If any file type of your need doesn't appear in that file, you can launch the scraper with a custom list of file types the following way:

```
./scrap.sh -o /path/to/output/folder -f /path/to/filetypes.txt
```

## Author

Xabier Lahuerta Vázquez. Contact me [here](mailto:xabier.lahuerta@gmail.com).

## License

[GPLv3](LICENSE)

