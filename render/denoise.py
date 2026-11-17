import cv2, numpy as np, sys
import os
S=os.environ.get('LEDSTAR_WORK','work')+'/'
src,out=sys.argv[1],sys.argv[2]
im=cv2.imread(src); m=cv2.imread(S+'mask_0001.png',0)
m=cv2.resize(m,(im.shape[1],im.shape[0])).astype(np.float32)/255
bg=cv2.fastNlMeansDenoisingColored(im,None,14,14,5,15)
bg=cv2.bilateralFilter(bg,9,40,9)
fg=cv2.fastNlMeansDenoisingColored(im,None,5,5,5,15)
m3=cv2.GaussianBlur(m,(0,0),1.2)[...,None]
res=(fg*m3+bg*(1-m3)).astype(np.uint8)
cv2.imwrite(out,res)
