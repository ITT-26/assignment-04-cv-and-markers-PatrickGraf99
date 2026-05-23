[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/5NorvP5a)

# Guide

## venv

It is recommended to create a virtual environment at the root of the repo. Do this anyway you like at the root of the 
repo and the use pip install requirements.txt to install all required packages. Every console command assumes you are
using Python inside said venv, if not you may have to adjust your paths. For simplicity I recommend using PyCharm
and its built in run functionality.

## Perspective Transformation

The script expects 3 named arguments to run, being -i for the input path, -o for the output path and -s for the target 
size of the resulting image in the format WIDTHxHEIGHT

An example could be ``python .\perspective_transformation\image_extractor.py -i .\perspective_transformation\sample_image.jpg -o .\perspective_transformation\out.jpg -s 1000x600``

(This is considering your .venv sits at the root of the repo, you may have to adjust paths on your machine)

The program will not run if any argument is missing, If -s contains the wrong format the script will default to using
the same dimensions as the image has.

Clicking with the mouse in the picture will set an anchor point. Clicking c will delete the last point, clicking escape
will reset the program completely, clicking s will save the image to the specified output path and clicking q will
close the program

The order in which you select the points does not matter, the program calculates which point is the top left, 
top right etc. and displays the result with the correct orientation. (If for some reason you want to change this 
behavior go to line 50 and replace ``sorted_points`` with ``selected_points``. Should you do this the first selected 
point will always be considered top left, the second top right, the third bottom right and the last bottom left. This
does of course warp the image in different ways and does not keep orientation)