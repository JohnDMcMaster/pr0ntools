pil_image = PIL.Image.open('Image.jpg').convert('RGB') 
open_cv_image = numpy.array(pil_image) 
# Convert RGB to BGR 
open_cv_image = open_cv_image[:, :, ::-1].copy()


