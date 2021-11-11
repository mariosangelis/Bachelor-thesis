# import the necessary packages
from skimage.measure import compare_ssim
import argparse
import imutils
import cv2
import sys

def main():
	
	# load the two input images
	imageA = cv2.imread("images/9.jpeg")
	imageB = cv2.imread("images/18.jpeg")
	# convert the images to grayscale
	grayA = cv2.cvtColor(imageA, cv2.COLOR_BGR2GRAY)
	grayB = cv2.cvtColor(imageB, cv2.COLOR_BGR2GRAY)
	
	# compute the Structural Similarity Index (SSIM) between the two
	# images, ensuring that the difference image is returned
	(score, diff) = compare_ssim(grayA, grayB, full=True)
	diff = (diff * 255).astype("uint8")
	
	print(diff)
	print("SSIM: {}".format(score))
	
	import os
	duration = 1  # seconds
	freq = 440  # Hz
	os.system('play -nq -t alsa synth {} sine {}'.format(duration, freq))
	
	

if __name__ == '__main__':
    #argv[1] is the port for the socket to bind
	if(len(sys.argv)<2):
		print("Wrong number of arguments")
	else:
		main()



