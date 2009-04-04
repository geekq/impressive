import impressive
import unittest

class Geometry(unittest.TestCase):
    def testParsing(self):
        c = impressive.FrameCoordinates("1024x768+1280+0")
        self.assertEquals(1280, c.offset_x)
        self.assertEquals(0, c.offset_y)
        self.assertEquals(1024, c.width)
        self.assertEquals(768, c.height)
     
    def testParsingException(self):
        self.assertRaises(ValueError, impressive.FrameCoordinates, "1024x768 1280+0")
	
    def testTuple(self):
	self.assertEquals((640,480,640,0), impressive.FrameCoordinates("640x480+640+0").as_tuple())
     
if __name__ == "__main__":
      unittest.main()

