# Google Takeout Photos Recover Metadata
This parses all files - images and videos - and add the metadata present in the json side car files.

## Motivation
My mom told me that her google account was full. Because it's my mom I had to jump in.

Google offers 15Gb of data and almost all of that space was occupied by photos and videos.
I searched online for how to back up those in order to delete from Google's cloud.
I came across Google Takeout, a tool to export all sort of data from Google. I just wanted photos
so I went for Google Photos only. When the export was done I downloaded and got confused - why do
I have json files here? Started searching online and I started to understand what they are.


I started my search for a tool that would write the metadata to those files. Interestingly enough
I could not find one that suited my needs. Some tools do not support some type of files, like .gif or .mp4.
Others would only write date and time information without supporting GPS information.
Others were written in weird languages like JavaScript :D. Basically I was expecting to find
a nice tool written in Python that would do the job. Because I could not find one here is my attempt.

## Installation

I developed this tool on a MacOS. It should be identical for other platforms.

### Requirements
You will need Python3 installed.

The following packages are required as this tool depends on them:

```sh
brew install exiftool
brew install libmagic
```

After having the above packages installed I recommend using a python virtual environment to run this tool. For that do the following:

```sh
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Running the tool
For running this tool you will need to provide the folder containing all the exported photos from Google Takeout.

Unzip all files. If you have more than one file you have to copy all folders - the ones ending with `0001`,
`002`, etc. to the main `takeout` folder and provide it as input to the tool.

```sh
python main.py takeout recovered
```

The above command will run the tool and write the photos and videos with EXIF metadata into `recovered` folder.

### Important Note
Always back up your photos and videos beforing running this tool. I am not responsible for any damage it might cause to
you.

## Supported file types
Right now this tool supports the following file types:
- jpeg
- heic
- tiff
- png
- webp
- gif
- mp4

## Supported EXIF Tags
The tool writes date and time information, GPS information and title and description information. The tags used are:
- DateTime
- DateTimeOriginal
- DateTimeDigitized
- GPSVersionID
- GPSLatitudeRef
- GPSLatitude
- GPSLongitudeRef
- GPSLongitude
- GPSAltitudeRef
- GPSAltitude
- Caption
- Description
- ImageDescription
- Title
- ObjectDescription
- PreservedFileName

## Known limitations
This tool does not consider edited files. I know there are some filenames that have the `-edited` suffix but do not
contain an associated json side car. In my case none of my files have the `-edited` suffix so I did not add support for
it because I could not test it. If you want to add support for that feel free to open a PR.
