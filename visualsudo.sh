#!/bin/bash
DIRECTORY=$(cd `dirname $0` && pwd)
osascript -e "display dialog \"BrewStore needs administrative previlidges to continue with the requested progress. Please enter your system password\" default answer \"\" with icon file (POSIX path of file \"$DIRECTORY/icons/brewstore_v1_1280.icns\")  buttons {\"Continue\"} default button \"Continue\" with hidden answer with title \"BrewStore Password needed\"
set w to text returned of the result
do shell script \"echo \" & quoted form of w"
