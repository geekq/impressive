import impressive
import unittest

class Geometry(unittest.TestCase):
    def testParsing(self):
        c = impressive.FrameCoordinates.parse("1024x768+1280+0")
        self.assertEquals(1280, c.offset_x)
        self.assertEquals(0, c.offset_y)
        self.assertEquals(1024, c.width)
        self.assertEquals(768, c.height)
     
    def testParsingException(self):
        self.assertRaises(ValueError, impressive.FrameCoordinates.parse, "1024/768 1280+0")
	
    def testTuple(self):
	self.assertEquals((640,480,640,0), impressive.FrameCoordinates.parse("640x480+640+0").as_tuple())

    def testOffsetIsOptional(self):
	c = impressive.FrameCoordinates.parse("800x600")
        self.assertEquals(0, c.offset_x)
        self.assertEquals(0, c.offset_y)
        self.assertEquals(800, c.width)
        self.assertEquals(600, c.height)

    def testStr(self):
	c = impressive.FrameCoordinates.parse("800x600")
	self.assertEquals("size 800,600 offset 0,0", str(c))

    def testAspectRatio(self):
	c = impressive.FrameCoordinates.parse("400x600")
	c.adjust_to_aspect_ratio((4,3), (1,2), (2,1))
        self.assertEquals(400, c.width)
        self.assertEquals(300, c.height)
        self.assertEquals(0, c.offset_x)
        self.assertEquals(100, c.offset_y)
	
     
if __name__ == "__main__":
      unittest.main()

