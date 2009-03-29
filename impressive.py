#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
#
# Impressive, a fancy presentation tool
# Copyright (C) 2005-2008 Martin J. Fiedler <martin.fiedler@gmx.net>
# portions Copyright (C) 2005 Rob Reid <rreid@drao.nrc.ca>
# portions Copyright (C) 2006 Ronan Le Hy <rlehy@free.fr>
# portions Copyright (C) 2007 Luke Campagnola <luke.campagnola@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License, version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

__title__   = "Impressive"
__version__ = "0.10.2"
__author__  = "Martin J. Fiedler"
__email__   = "martin.fiedler@gmx.net"
__website__ = "http://impressive.sourceforge.net/"
import sys
def greet(): print >>sys.stderr, "Welcome to", __title__, "version", __version__
if __name__ == "__main__": greet()


TopLeft, BottomLeft, TopRight, BottomRight, TopCenter, BottomCenter = range(6)
NoCache, MemCache, FileCache, PersistentCache = range(4)  # for CacheMode
Off, First, Last = range(3)  # for AutoOverview

# You may change the following lines to modify the default settings
Fullscreen = True
Scaling = False
Supersample = None
BackgroundRendering = True
UseGhostScript = False
UseAutoScreenSize = True
ScreenWidth = 1024
ScreenHeight = 768
TransitionDuration = 1000
MouseHideDelay = 3000
BoxFadeDuration = 100
ZoomDuration = 250
BlankFadeDuration = 250
MeshResX = 48
MeshResY = 36
MarkColor = (1.0, 0.0, 0.0, 0.1)
BoxEdgeSize = 4
SpotRadius = 64
SpotDetail = 16
CacheMode = FileCache
OverviewBorder = 3
OverviewLogoBorder = 24
AutoOverview = Off
InitialPage = None
Wrap = False
AutoAdvance = None
RenderToDirectory = None
Rotation = 0
AllowExtensions = True
DAR = None
PAR = 1.0
PollInterval = 0
PageRangeStart = 0
PageRangeEnd = 999999
FontSize = 14
FontTextureWidth = 512
FontTextureHeight = 256
Gamma = 1.0
BlackLevel = 0
GammaStep = 1.1
BlackLevelStep = 8
EstimatedDuration = None
ProgressBarSize = 16
ProgressBarAlpha = 128
CursorImage = None
CursorHotspot = (0, 0)
MinutesOnly = False
OSDMargin = 16
OSDAlpha = 1.0
OSDTimePos = TopRight
OSDTitlePos = BottomLeft
OSDPagePos = BottomRight
OSDStatusPos = TopLeft


# import basic modules
import random, getopt, os, types, re, codecs, tempfile, glob, StringIO, md5, re
import traceback
from math import *

# initialize some platform-specific settings
if os.name == "nt":
    root = os.path.split(sys.argv[0])[0] or "."
    pdftoppmPath = os.path.join(root, "pdftoppm.exe")
    GhostScriptPath = os.path.join(root, "gs\\gswin32c.exe")
    GhostScriptPlatformOptions = ["-I" + os.path.join(root, "gs")]
    try:
        import win32api
        MPlayerPath = os.path.join(root, "mplayer.exe")
        def GetScreenSize():
            dm = win32api.EnumDisplaySettings(None, -1) #ENUM_CURRENT_SETTINGS
            return (int(dm.PelsWidth), int(dm.PelsHeight))
        def RunURL(url):
            win32api.ShellExecute(0, "open", url, "", "", 0)
    except ImportError:
        MPlayerPath = ""
        def GetScreenSize(): return pygame.display.list_modes()[0]
        def RunURL(url): print "Error: cannot run URL `%s'" % url
    MPlayerPlatformOptions = [ "-colorkey", "0x000000" ]
    MPlayerColorKey = True
    pdftkPath = os.path.join(root, "pdftk.exe")
    FileNameEscape = '"'
    spawn = os.spawnv
    if getattr(sys, "frozen", None):
        sys.path.append(root)
    FontPath = []
    FontList = ["Verdana.ttf", "Arial.ttf"]
else:
    pdftoppmPath = "pdftoppm"
    GhostScriptPath = "gs"
    GhostScriptPlatformOptions = []
    MPlayerPath = "mplayer"
    MPlayerPlatformOptions = [ "-vo", "gl" ]
    MPlayerColorKey = False
    pdftkPath = "pdftk"
    spawn = os.spawnvp
    FileNameEscape = ""
    FontPath = ["/usr/share/fonts", "/usr/local/share/fonts", "/usr/X11R6/lib/X11/fonts/TTF"]
    FontList = ["DejaVuSans.ttf", "Vera.ttf", "Verdana.ttf"]
    def RunURL(url):
        try:
            spawn(os.P_NOWAIT, "xdg-open", ["xdg-open", url])
        except OSError:
            print >>sys.stderr, "Error: cannot open URL `%s'" % url
    def GetScreenSize():
        res_re = re.compile(r'\s*(\d+)x(\d+)\s+\d+\.\d+\*')
        for path in os.getenv("PATH").split(':'):
            fullpath = os.path.join(path, "xrandr")
            if os.path.exists(fullpath):
                res = None
                try:
                    for line in os.popen(fullpath, "r"):
                        m = res_re.match(line)
                        if m:
                            res = tuple(map(int, m.groups()))
                except OSError:
                    pass
                if res:
                    return res
        return pygame.display.list_modes()[0]

# import special modules
try:
    from OpenGL.GL  import *
    import pygame
    from pygame.locals import *
    import Image, ImageDraw, ImageFont, ImageFilter
    import TiffImagePlugin, BmpImagePlugin, JpegImagePlugin, PngImagePlugin, PpmImagePlugin
except (ValueError, ImportError), err:
    print >>sys.stderr, "Oops! Cannot load necessary modules:", err
    print >>sys.stderr, """To use Impressive, you need to install the following Python modules:
 - PyOpenGL [python-opengl]   http://pyopengl.sourceforge.net/
 - PyGame   [python-pygame]   http://www.pygame.org/
 - PIL      [python-imaging]  http://www.pythonware.com/products/pil/
 - PyWin32  (OPTIONAL, Win32) http://starship.python.net/crew/mhammond/win32/
Additionally, please be sure to have pdftoppm or GhostScript installed if you
intend to use PDF input."""
    sys.exit(1)

try:
    import thread
    EnableBackgroundRendering = True
    def create_lock(): return thread.allocate_lock()
except ImportError:
    EnableBackgroundRendering = False
    class pseudolock:
        def __init__(self): self.state = False
        def acquire(self, dummy=0): self.state = True
        def release(self): self.state = False
        def locked(self): return self.state
    def create_lock(): return pseudolock()


##### TOOL CODE ################################################################

# initialize private variables
FileName = ""
FileList = []
InfoScriptPath = None
Marking = False
Tracing = False
Panning = False
FileProps = {}
PageProps = {}
PageCache = {}
CacheFile = None
CacheFileName = None
CacheFilePos = 0
CacheMagic = ""
MPlayerPID = 0
VideoPlaying = False
MouseDownX = 0
MouseDownY = 0
MarkUL = (0, 0)
MarkLR = (0, 0)
ZoomX0 = 0.0
ZoomY0 = 0.0
ZoomArea = 1.0
ZoomMode = False
IsZoomed = False
ZoomWarningIssued = False
TransitionRunning = False
CurrentCaption = 0
OverviewNeedUpdate = False
FileStats = None
OSDFont = None
CurrentOSDCaption = ""
CurrentOSDPage = ""
CurrentOSDStatus = ""
CurrentOSDComment = ""
Lrender = create_lock()
Lcache = create_lock()
Loverview = create_lock()
RTrunning = False
RTrestart = False
StartTime = 0
CurrentTime = 0
PageEnterTime = 0
TimeDisplay = False
TimeTracking = False
FirstPage = True
ProgressBarPos = 0
CursorVisible = True
OverviewMode = False
LastPage = 0
WantStatus = False

# tool constants (used in info scripts)
FirstTimeOnly = 2

# event constants
USEREVENT_HIDE_MOUSE = USEREVENT
USEREVENT_PAGE_TIMEOUT = USEREVENT + 1
USEREVENT_POLL_FILE = USEREVENT + 2
USEREVENT_TIMER_UPDATE = USEREVENT + 3


# read and write the PageProps and FileProps meta-dictionaries
def GetProp(prop_dict, key, prop, default=None):
    if not key in prop_dict: return default
    if type(prop) == types.StringType:
        return prop_dict[key].get(prop, default)
    for subprop in prop:
        try:
            return prop_dict[key][subprop]
        except KeyError:
            pass
    return default
def SetProp(prop_dict, key, prop, value):
    if not key in prop_dict:
        prop_dict[key] = {prop: value}
    else:
        prop_dict[key][prop] = value

def GetPageProp(page, prop, default=None):
    global PageProps
    return GetProp(PageProps, page, prop, default)
def SetPageProp(page, prop, value):
    global PageProps
    SetProp(PageProps, page, prop, value)
def GetTristatePageProp(page, prop, default=0):
    res = GetPageProp(page, prop, default)
    if res != FirstTimeOnly: return res
    return (GetPageProp(page, '_shown', 0) == 1)

def GetFileProp(page, prop, default=None):
    global FileProps
    return GetProp(FileProps, page, prop, default)
def SetFileProp(page, prop, value):
    global FileProps
    SetProp(FileProps, page, prop, value)

# the Impressive logo (256x64 pixels grayscale PNG)
LOGO = '\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x01\x00\x00\x00\x00@\x08\x00\x00\x00\x00\xd06\xf6b\x00\x00\x0b\xf1IDATx\xda\xed[y|OW\x16\x7f\xbf\xfc\x12\x12K\x13\xb1\xc4R\x11\xbbN,c\xadHF\xa8\xd6RK\xa7Cf\x08>\xaa\xed\xa0\xa5\x8a\xd8\xe9Hc\x9dRK\x19'+\
'\xb4b\xd4V{\x8d}\xcd\xa0\x944\xb6PF\xc6RU\x82\xa4\x96HD\xf6\xbc\xfe\xee9\xf7\xdew\xee{?Lc>\x9fL\xe6\xe7\xfe\x11\xf7\x9c\xbb\x9c{\xcf\xbb\xf7\x9c\xef9\xf7G\xd3\x9e\x97\xe7\xa5\xa8\x97\x12#7\xdfN:2\xbc\x98\xab\xee\xbf\xd2\t\x1dJB\t\xd7\xdc\x7f\xe9\xeb:/'+\
'\x13\x9fa\x96\xe0O"\xeb\x16Q\x05\xf4\x12\xfb\xd7\xbf)\xf8$C\xf3u=\xa3C\xd1T\xc0F\xa9\x80\x1b\x05\x9e\xc3\'\x93\x8d\xbfZ4-`\xbaT\xc0\x99\x02O\xd2\n\'(U\x14\x15\xd0X\xee__W\xe0I*\xe6\xb3\xf1?\x17\xc9\x13\xd0\xd5P\xc0\xc7\x05\x9fe\xa6cx~\xbf\x82\x8e\x8e'+\
'\\\xeb(S\x0bI\x01\xef\x19\n\xe8\xf5\x0c\xd3\xbc\xb5u\xedk\x05\x1e|\x8dI\xdfTH\n\x98j(\xa0q!-\xa1x\x1e\x93>\xa3\x90\xa4/\x97\xfb\xcf/, T\x0f\xc4\xbf[H\xd2\xf7J\x05\xfcXXf\xa8\x0b\x88\x0f-$\xe9\xdfI\x05l-,\x05\x0c\x03\xf1\x95\x0bI\xfa\x05\xa9\x80\x91'+\
'\x85\xa5\x80\xf9L\xfaCV+\xe3\xfd\xab\xedG\xf9\xc7a3/\xa7\xec\x92\xa5\xcd\x9c\x9bR\x01\xcd\xfec\xa9\x1e~6\x95\x11\xd4\xc6Q\xeaa\xbd.\xab\x87`\xbd\xc1\x90\xd9_M\xedCv\xe5\xd19b\xf1\xd2\x0fB\xdc\x94\xd1\xbb\x98\xf4ko}\xba\xc7\xb1\x96\xcc3\x7f\xa9c\x92'+\
'\xe6\xcd&l\xe3\xeb\xa8\x15\xeb3k\xd5\xc4v\xb2\xa1\xfc\x07\xdf\xde\xd5\xf5\xa4\xed\x91\xadM#~\xbb\xe4p\x92\x9ewi\xf3\x94\xf6\n\xbb\xda\xbc\x98\xeb\xf9\xfa\xb5\x9d3\xc3\xec\x84\xfbP\xec\xff\x01pC\x98\xb0\xea\nT\x04\xf9U\x05\xf9B\xff\xfd\xc9\xf9\xfa'+\
'\xfd}\xd3^7\xba\xb8\x01\x12\xfe\x14\x89m\xac~\xd1Q\xb1\xf59\x863\xdf\xec!\xc6\x8e\xe2\x81\xd7\xfeJT\xc2%])y\x9f\xab_\xb5;p\x9bhZ\xe8UV\x89\x17\xeb\x9a\x99#\x87\xcc\xf5 \xfd\xcb.\xca\x93\r\xb1\x86\n\xbc"\x1fI\xf6\xbf\xc3\xe5\'\xb0K\xe6\x0e\xa0OZ '+\
'\xe18X\xd4KH\xb8\x8f1\x90\xf3Z\x89|\xab\x01\xfd\x1e\x12\t\xac\xbeM\xd3\x02b\x8c=\xa1\x06\xda\x1a\xa7-\xf97\x86\x00\xf7\x1c\xddTn7\xa2\x0b\x18\xc3av\xdd\xfb:Q@\xcb+t\xc4\xd1\x17e\xf7\xcaI\xca\\\x87\xf9\xf1\xf0:\xab\xb0\xcf\x8b\x8fRF\xb2F\x01\xbd'+\
'\xc0\xec\x0fJ\xdfe\x9c\xd5\xfcx\x9f\xa6\x93\\\x08\xe4}\xda\x01\x89@\xc8\x9e\xc5\xea\xb3\xb4\xb04\xd2\xf3\xe7\n\x8e\x86\xa8<\xc2\xd9mH\xa8\xa1[\xca\xfd\x96d\x05K\x18\'Q+\xcb\x0f\n* $M\x1d\x91\\\x81\xf7\xb6\xed5\xcd\x15O\x0c\r)\x99\xbc\x7f\x80'+\
'\xe44\x07:\x1c\xea~\x86\xf8\x89\x8c\xce\xc5X\xbf\xceMu\x92\x87\\\x03\x03\x81\xc2\x8bS\x1d\x9d\xfa\xbb\xb0\xdb\xeb\xbbn`\xcf\xf1\x9a\xdbj\xf6o\xce\xd9\x1d\x89\xc8\xe9(\xef\x0f"\x91Ss\xfe\xe8_;l\xeayl\xbdEVp\x801\xfe\xe9q\x90n(\x08\xf7\x9f\xb1k\xc6'+\
'\xb8u8\xe1\xe7\xbc\xf7\x87\xbc\xdb\x9dTE\x01\x1d\xc5E\xbfgR@C\xb1\x99T;Y\x7f7\xc3\x02\xc1\x80\x15\xd8\x86\xbb\xc9\x8d\x993j\x05\x1e\xc0=F$\xa0g\xe3\x04\xafA\xc3&\xf6g}s\x9bf\x8b\x04\xfa\xa0\xb6\x90\xadw\xaec_\xf6E\xc0Y..\xc0W(?\x80[\xf5Y\x10W\xe9{'+\
'\r\x05\x80\xddX\xb4\x94~Qo\xb4%G\xe0\xbb\x94\xde\x0c\xabj\x80\xbdOA\xcb\x02\x7f\xcd\xdet\xd8\xa6t\xa9\x00\x94\xb2\xae\x9ef\x0b\x1c\xb8\xea\x0eQ\xc0\xef\xc4\xbc;9\xe36#\x8c\xc0d\x12L^\x0b\x96\x8a\x90\xe1\\\x0b0\xe7\xb8\r\xb4\x84\x9b\x85\xdds\x94\xf7'+\
'\xc5\x84\xd9C\x90q\x1c\x889\xacGm`x&\xc3\xe2\xb9\x80\xc5\xd8;KZ\xa5W\xc0\xa2\xea\x9d\x05\xed\t\x1aa\xe1\xc2\x95\xd9\x1d\xab\x84\xaf\x8e\x91\xf0u\x97\x1b=\xf5\xfbP\x9f\x99t\xfd\xfe_\x0b\x05\xc0\xc9Z/\xee\xfd\xc2<\xa9\x80\xceb\xbd\xa39\x036\xb3_z\xd3'+\
'\x14F.3t\xa1\xc7{\xd1\xaby\xc1\x9dU\xbf\'\x1a\x9c\xc3\xe7K\x14\xd7x\x944Ge9g\x15\x18:\xac\xf7\xe0\x8d\t\xe6\xe8D(H\x0b\x14\xe3\xcfJw\xda\x16\x91\xab\xaf\xa0[\x02\rv\xb5\xbe\tTu\xba\x0c\n\xf0\xcce\xecW$\xbbY\x9cP@\xb8\x98\xfee\xce\x18\r7E|\x8f(\xb8'+\
'\xb85\xc0\x00\x80\xb1N\xa9)\xe6\xf0\xcf\x12G\xc0\x06\xfe\xe53\xe2\x05u\xfd\xae4\xf3=\x85\xd3(.8\xd3\x80\x06\x11U\xef\xeb{/2j;\xc1*x\xbe\xabq\xf2\r>\xfe\xa7*\xb2\xc7v\xd3=\xc5/\xd0\xdd\xb0\xc7\xc1F\x93go\xf6\xb7\n\xb0\xdf!\x9e\xbb?\xaf\x0c\xe2\xd3'+\
'\xa7\xb9+w\x82/\xdf\xf7\x01#\xa2\r\xff\xa0\x0f5\xe6\x80\xadF\xc8\xd9\x87\x12/\xa8\xa7\x1bf\xfc\x0f\xdc\xec\xdb\xd5O\x0c\xc8O\xfb\xbb\x1e\x83)\xa9\xb9\xc4\xec\x0f\x80\x01\x9d8\x15\x81\xe3\xef\x19\x8e\xb36\\\x8a\xcb\x04M\xfd\x831\xc6\x19\x1ey\x93\t'+\
'\xa8i6\x10r\xba\xb8\x15\xd4\x8d\xe1\n\xd8%\xf1B6#\xfb\x93\xa5f\x83}\xf2\x06\xbb\xfb\x80 \xc9\xb9\xc2\xf8\x86\x92K\x8b^0\xbb\xa39\xe1p\x81\xc0\xc1/\xe1\x83\xc2Vr\x0f\x95\xa8\x0c\xedC,I\xaa\x08N-2y\r~,\xf5\x0f5\xd3R\xbe\x84\x9d\xa2O\xd8^\xc6\xb4Op%'+\
'\xfa\x89\x80\xc7\xa6\x03\xc6J\x0e\x18\xad\xc5\x88\xa9R\r\x07\xf36t\x9bc\x8ea\x0e:*\xef@S]\xe2E\xc6\x92n\x1f\x03\xa7!\xe1\x1c\x02\x8c\xc6j\xb3N\x95\xd2Z\x9b\xf7\xa7\x95\x02\xceRN\xed\x03\xeak\xd2~XwZ\x8eA\xe3x$~h\xa2\xee\x93\x9f\xc3{\xaf\x9b\x15'+\
'\xb0\x80\x8f6\x8e\xecg\x86\xf3\x9c\x01\xf6\xd9\x1f\xea\xcb\x9cK\xbd\xe5h\x9a\x0eX\x11\x1f\x96\xda\x03\xb7-\x91\x00&\xef\x11=\x93\xf0\x91V\xb2\xda\x0e\x7f\xa1\xd9Z\x9a\xb9\xc31N\x00\xfe\xcd$\xe8\xdc+\xcb\xf9R\xd0\x8e\xfa\xfe\x84T\x86\x9a_\xb0'+\
'\xc7\xf1\xa4\xc7d5\x0e\xd1VpH\xe3\xae\xbe\x13\xe4\xb2\xe4Hy\x88\x13\x16"\xfb\xb2s\xa9\xcc\x98n 9q\xf4\x82U\x89\x84X\xc6\xf8\x9e\x06d\xd0e\x12\x843\xc2$\xe6\xb8\xd3E\xc5\x117Q\x0c\x10\xd5<\xd2\xdaR\x7f\xd2\t\xd0\x1a\n\x04\xb4L\x89\x07+^\xe3'+\
'\xec}j\xa4\xb1E\xa7\x88\xc6\xc0\x86\xad\x05\xbe\xc9D\x94\xed\xa3?\xfe\x04\x9c6\xdc0z\xc1\x0c\xfa\xbd\xef\x98Op#\x18\xd8[\x90\xeb\x19uEY\x14\x80\xaf\x0b\x1c}C\xef\xbe\x964nb\x82\xb9|\xc1\xdb;\x88\xf8\xeeLm:i}\x01co\x04[\x8d\x03ZP\x1a ;"\x03?'+\
'\xb0\x9c\xf3\xb9\xe5E\xc4m\x91\xcaB\xa84\xc3j\xa0\x87:Of\xc3`\xe3\xaf\x96\xe8N\xb8]\x84n{\xe8\x9a\xd0\xab\x1c\xa0@%\x88\xe6_-F\xc3T\x02/\n\xdc\xdb\x85\xb2+\x1d\xe1\xec\x9c\xc1\x84\x8b\xc8Q\x11\x000v\xa3\xa6\xcd\x86\x8fY\x99\x9e\xbbAN\x1f'+\
'\x05h:\x05\xbc\xe0\x16\xd2\xda\xdc\x92\xf0\x1b\x0b\x1c\x89b\xe0\xc4\xfe\x8dN\x88\xb8}\rM\x17\xd1c;\xfc\xa9\x19\\\xef\xad|\xab\x19AJ\x1aC\x18\xbc|\x92\xff\xae^\x0f\n\xcd\x10\x8c\x840F\xab\xf8\x88\xfa\xe7N0\xf2Mg\xe2B\xa0\xe9\xf7J,\xa8\xa9'+\
'&EI\xf8E\x839\x16\x94\x1f\xb4\x0f\xd7\xcc\x0b\x10,X\xf4\x03\xda\xdcW\xc1IN\x8b-*\x9f\x07\x89JjC\xeb\xcf\xedgf\xf0\x93F\x07#\x9a\x9c\x07\xd6\xbb\xa2\xf2!\x9d&.\xf1H\xd6\'^\x90\x1e\x94\x8f,\t?\xf0\x82q\xaa\xb4\xaet\xc2\x18\x8a\xc5v\xb3\xfa'+\
'I\xda\xfc24\xb7zr\xd2\xaa\x077\x04\x1bL\xa9\xab[\x1cVK+U\xb9k\xdf@\xbb\xda\xc9\x13\xa0\xd0\x90\x0c\x92\xe5q\x9c*\x18\x17\xeeL\xd6\x14\x92SG/\xf8\xaa\xd9\xcd<\xb4$\xe1V\x0b\xaa\x1f\x8cx\xc9b#\xaek\xc4\xfb(\x19\x1a_h\x7f\xfb)i\xbbFW1\xbddJ'+\
'\xb0U9\xae\xd3X+`?\xa4\xac\xba9I\x14\x83\x05L\xaf \x99\x10\xc2E9\x13\xb5\x16\x13\x16P\x06\xd3\xd0\x16\xcaQ\x9a\xc62\xbc\xa0|\x86\x9b\x0c\xcb$\x18\xb5$:\xf2H\x9a.R\x9f\xcd E\xf3\xc9\xd3\x12\x97\xe5b\x9d\xa6z=\xf15\x1c\xe1}\x90H\xab\xa8\x02'+\
'\xe6J\'G\xa4|K\xe3I\xa5\xc0\x0fL\x0e\x11/\x98E\xb1F\xb2\xf9 6R\xfd\xda\x1a\x08vI\xfbt4\xe0>H\xd5r\xf2\xb9!\xd5x\xda\xcd\xd9Zh\xce\xb7\x83\xb1S\xca\x0e\xc8\x97\xc1\xa6\xd7E\xf9(\xa4\xe4U\xff$3>\xc4\xf8\x02\x12\xbcY\xd2\x89\xd0\x14\x02\\\xb7'+\
'\x9bB[~u\xa6\xd1\xdb\xa9\xba\x1d8\x921\xc4\x02\xa1\x9d\x9a\xacx\x045\xed\x0b\x81\xb8>@]EU\xc8#\xc6D\x19\xbft\xb2\xdf\x96\xce\xe4\x8b\xa5\xde&$}\xda8\xaf\x18\xab\xd3\xb9\xfc\x05w:aFXv\xc2\x82\x05\x87)*G\x81D\x82)\xb4\xd5\x9a\xea$\xb6"^\xb0'+\
'\x9c \xef\xd3|\x96\xc3\xedc\xea\xf6\x9cx\xa6\x1b\xe2\xe4\xd1\xa4\x05\xe6\xbc|\xe9\xc1\xfe(\xbd\x1d~\x0c\xcc\xd7\x18\x87o\x1c^\xea\xc4\xae\xaa\x02\x96\xab\xcf\x82\xfa#\xbb\x05\x8b\xebzjY\xc2\xf3\x83/\x93E\xc1\x95\xfd\xfd\xbb\x7f\x16\x08!'+\
'\x0c9\xd9\xe6\x88\tOS\x08\xe1@n+E\xaa\x90$d\x1d\xd4|\xcc\x10\xa7\xd6U\xaec\xba\xe9\xcc!\xa2\x89\x0f\x94\x8c7\x1d\x16\xefE\x1e\x0c\xe7\xce\xf4\xa2G\x8dE\xd5n\xcc\xa0\xad\xe6\xbbi\x92-\x9dl\x1c\x81\xb45\xa8\x80\r\xc8\x9b\xa2H]\t\xbc\xab\xc6^B'+\
'\xcf\x80_\xec#\xd2\xf62\xc1K\x81\xd6\x04s\x92U\xfb\x06\xe2R\xd5\xa7\x01\xbe(\xd6~~\n\n\xce\xed\xae\xe6>\xce\x9a\x14\xd0\x1c\xd5\x941\x82\xcd\xeb\xd9j\x04\xcb\x97\xa6\xb1\x86n\x98\x8c\xd98\xa8\xb6\xe63\x1c\x0c\\\x0e\xebR\x07/\xf4\xce\x88F\xb6'+\
'\x92\xbdo\x1a^t\x8d\xb1\xff,\xe5G\x82#\xd0\x0e\xa91u\xb5\x07\xe8W\xa6\xb1H\xc7\xa3\xe9`@[\x954\r\xb3\x9e/\x10/H\x7f,\x05\xa6#\xd5\xe2\x05\xd7\n\xaa7f\xe9cc\xcf%\xe5\xca\xe3\xf8\x86\xd1;\xc1\x1cI\x10p\xc1"\xa6\xbdq\xd9X;)S\xd8\x98\xe0\xe1\xff'+\
'F\xd2\xbc\x9bC\t"=E\xf6\xa9+\xb8\x04\xbd\x83\xee\xcc\xe7\xf5\x15\x9d\xef\x1d8\xcc\x1fY\xd2D\xb8\x9bL\xbd`M\xf3i=i\xf1\x82\xc2\xc6q\xf5)\xe5.\xc18\x88,-.\xcf-\xda2j&\xa4\xed\xb6\x9a\xb8\xc7!\xca\xf4\x8b\xceU\xd9\x89h?|nHN\x17\xf5\xc5\x91\x89M'+\
'\xf1y\xac\xdee\xd9&\xc2\xdd\xa3\xc4\x0b*\xa1\xedm\xe5{K/\xd8O\xc9\x16\xd0\x92\xb3\xa8\xa2f\x0eM\x07X]\xcf\x8c|e\xd4Q\x81QC\x8fS\xf6%aK\xea\xefT^Q\xda\x08\x1f#\x1e\xa5\x96\x98\xa6?&\x02v\xb5\x0cTS\x11\xff\xean\x13\xe1\xeeJrc/Q\xbf\xac~oy\x1c'+\
'\x83\x95l\x01\xf9\xfa\xcbU\xe4\xf6*p\xdb9q\xbe-\x8e\x19\xa3\xce\x12$m\xeb\xf5\x83\xbc\xd7\x93=\r~\xbbS\xd2\xe7G\x1b\xfe\xa3q<\\Q\x8b\x86\x1d\x81\xe0=g/\xd5\xb5\xc8\x11\xbb\xda\x0f=GqOG\xe1\x1f\xbd\x18\xab+\xe6\x841<\xa9\x8b\xb1\x03\xc7\xa6d'+\
'\x0b2SRR\x92\xce\x1f\xda8\xb9\x95\xdd|\xd6\xd5\xdeJi0~g\xfc\xads\x1b\xa2\xc2\x1b\xab\x98\xc8V3l\xda\xee\xeb\xdfE\x0f3\xa3\xe0\xae\x93\xb6\xfcxj\xc5\xe8\xe6J\xa6\xa8\xd9\xe0\t\xed\xad[\rZ\xbc\xf81\xbf\x98\xaa>l\xcb\x89\x1b\x17\xb7\xcc\xe8\xd7'+\
'\xc2\xe3\xbf\xf1\xd3\x00\xcc\xb3L\xd0\\\xb64\x03\x05\xf4t]\x05\xf4\xfc\x95?\xcd\xf8\xbf+\xe8\xb8}\\W\x01\xf0Fr\xc7u\xf7\x8fAv\xac\x0b+\x00~\xce\xb2\xcau\xf7_\x9a&\x7f\\\xb14\xb6\xbcz\xb8X\t\xb3<J\xb8X\x19gy\xf5p\xb1\xb2\xd4\xf2\xea\xe1b\xe5'+\
'\x90\xe5\xd5\xc3\xc5J\xe2\xb3\xfdW\xa5\xe7\xe5y\xf9\x1f(\xbf\x00\x8e\xf2\xeb\x86\xaa\xb6u\xc1\x00\x00\x00\x00IEND\xaeB`\x82'

# determine the next power of two
def npot(x):
    res = 1
    while res < x: res <<= 1
    return res

# convert boolean value to string
def b2s(b):
    if b: return "Y"
    return "N"

# extract a number at the beginning of a string
def num(s):
    s = s.strip()
    r = ""
    while s[0] in "0123456789":
        r += s[0]
        s = s[1:]
    try:
        return int(r)
    except ValueError:
        return -1

# get a representative subset of file statistics
def my_stat(filename):
    try:
        s = os.stat(filename)
    except OSError:
        return None
    return (s.st_size, s.st_mtime, s.st_ctime, s.st_mode)

# determine (pagecount,width,height) of a PDF file
def analyze_pdf(filename):
    f = file(filename,"rb")
    pdf = f.read()
    f.close()
    box = map(float, pdf.split("/MediaBox",1)[1].split("]",1)[0].split("[",1)[1].strip().split())
    return (max(map(num, pdf.split("/Count")[1:])), box[2]-box[0], box[3]-box[1])

# unescape &#123; literals in PDF files
re_unescape = re.compile(r'&#[0-9]+;')
def decode_literal(m):
    try:
        return chr(int(m.group(0)[2:-1]))
    except ValueError:
        return '?'
def unescape_pdf(s):
    return re_unescape.sub(decode_literal, s)

# parse pdftk output
def pdftkParse(filename, page_offset=0):
    f = file(filename, "r")
    InfoKey = None
    BookmarkTitle = None
    Title = None
    Pages = 0
    for line in f.xreadlines():
        try:
            key, value = [item.strip() for item in line.split(':', 1)]
        except IndexError:
            continue
        key = key.lower()
        if key == "numberofpages":
            Pages = int(value)
        elif key == "infokey":
            InfoKey = value.lower()
        elif (key == "infovalue") and (InfoKey == "title"):
            Title = unescape_pdf(value)
            InfoKey = None
        elif key == "bookmarktitle":
            BookmarkTitle = unescape_pdf(value)
        elif key == "bookmarkpagenumber" and BookmarkTitle:
            try:
                page = int(value)
                if not GetPageProp(page + page_offset, '_title'):
                    SetPageProp(page + page_offset, '_title', BookmarkTitle)
            except ValueError:
                pass
            BookmarkTitle = None
    f.close()
    if AutoOverview:
        SetPageProp(page_offset + 1, '_overview', True)
        for page in xrange(page_offset + 2, page_offset + Pages):
            SetPageProp(page, '_overview', \
                        not(not(GetPageProp(page + AutoOverview - 1, '_title'))))
        SetPageProp(page_offset + Pages, '_overview', True)
    return (Title, Pages)

# translate pixel coordinates to normalized screen coordinates
def MouseToScreen(mousepos):
    return (ZoomX0 + mousepos[0] * ZoomArea / ScreenWidth,
            ZoomY0 + mousepos[1] * ZoomArea / ScreenHeight)

# normalize rectangle coordinates so that the upper-left point comes first
def NormalizeRect(X0, Y0, X1, Y1):
    return (min(X0, X1), min(Y0, Y1), max(X0, X1), max(Y0, Y1))

# check if a point is inside a box (or a list of boxes)
def InsideBox(x, y, box):
    return (x >= box[0]) and (y >= box[1]) and (x < box[2]) and (y < box[3])
def FindBox(x, y, boxes):
    for i in xrange(len(boxes)):
        if InsideBox(x, y, boxes[i]):
            return i
    raise ValueError

# zoom an image size to a destination size, preserving the aspect ratio
def ZoomToFit(size, dest=None):
    if not dest:
        dest = (ScreenWidth, ScreenHeight)
    newx = dest[0]
    newy = size[1] * newx / size[0]
    if newy > dest[1]:
        newy = dest[1]
        newx = size[0] * newy / size[1]
    return (newx, newy)

# get the overlay grid screen coordinates for a specific page
def OverviewPos(page):
    return ( \
        int(page % OverviewGridSize) * OverviewCellX + OverviewOfsX, \
        int(page / OverviewGridSize) * OverviewCellY + OverviewOfsY  \
    )

def StopMPlayer():
    global MPlayerPID, VideoPlaying
    if not MPlayerPID: return
    try:
        if os.name == 'nt':
            win32api.TerminateProcess(MPlayerPID, 0)
        else:
            os.kill(MPlayerPID, 2)
        MPlayerPID = 0
    except:
        pass
    VideoPlaying = False

def FormatTime(t, minutes=False):
    if minutes and (t < 3600):
        return "%d min" % (t / 60)
    elif minutes:
        return "%d:%02d" % (t / 3600, (t / 60) % 60)
    elif t < 3600:
        return "%d:%02d" % (t / 60, t % 60)
    else:
        ms = t % 3600
        return "%d:%02d:%02d" % (t / 3600, ms / 60, ms % 60)

def SafeCall(func, args=[], kwargs={}):
    if not func: return None
    try:
        return func(*args, **kwargs)
    except:
        print >>sys.stderr, "----- Exception in user function ----"
        traceback.print_exc(file=sys.stderr)
        print >>sys.stderr, "----- End of traceback -----"

def Quit(code=0):
    print >>sys.stderr, "Total presentation time: %s." % \
                        FormatTime((pygame.time.get_ticks() - StartTime) / 1000)
    sys.exit(code)


##### RENDERING TOOL CODE ######################################################

# draw a fullscreen quad
def DrawFullQuad():
    glBegin(GL_QUADS)
    glTexCoord2d(    0.0,     0.0);  glVertex2i(0, 0)
    glTexCoord2d(TexMaxS,     0.0);  glVertex2i(1, 0)
    glTexCoord2d(TexMaxS, TexMaxT);  glVertex2i(1, 1)
    glTexCoord2d(    0.0, TexMaxT);  glVertex2i(0, 1)
    glEnd()

# draw a generic 2D quad
def DrawQuad(x0=0.0, y0=0.0, x1=1.0, y1=1.0):
    glBegin(GL_QUADS)
    glTexCoord2d(    0.0,     0.0);  glVertex2d(x0, y0)
    glTexCoord2d(TexMaxS,     0.0);  glVertex2d(x1, y0)
    glTexCoord2d(TexMaxS, TexMaxT);  glVertex2d(x1, y1)
    glTexCoord2d(    0.0, TexMaxT);  glVertex2d(x0, y1)
    glEnd()

# helper function: draw a translated fullscreen quad
def DrawTranslatedFullQuad(dx, dy, i, a):
    glColor4d(i, i, i, a)
    glPushMatrix()
    glTranslated(dx, dy, 0.0)
    DrawFullQuad()
    glPopMatrix()

# draw a vertex in normalized screen coordinates,
# setting texture coordinates appropriately
def DrawPoint(x, y):
    glTexCoord2d(x *TexMaxS, y * TexMaxT)
    glVertex2d(x, y)
def DrawPointEx(x, y, a):
    glColor4d(1.0, 1.0, 1.0, a)
    glTexCoord2d(x * TexMaxS, y * TexMaxT)
    glVertex2d(x, y)

# a mesh transformation function: it gets the relative transition time (in the
# [0.0,0.1) interval) and the normalized 2D screen coordinates, and returns a
# 7-tuple containing the desired 3D screen coordinates, 2D texture coordinates,
# and intensity/alpha color values.
def meshtrans_null(t, u, v):
    return (u, v, 0.0, u, v, 1.0, t)
         # (x, y, z,   s, t, i,   a)

# draw a quad, applying a mesh transformation function
def DrawMeshQuad(time=0.0, f=meshtrans_null):
    line0 = [f(time, u * MeshStepX, 0.0) for u in xrange(MeshResX + 1)]
    for v in xrange(1, MeshResY + 1):
        line1 = [f(time, u * MeshStepX, v * MeshStepY) for u in xrange(MeshResX + 1)]
        glBegin(GL_QUAD_STRIP)
        for col in zip(line0, line1):
            for x, y, z, s, t, i, a in col:
                glColor4d(i, i, i, a)
                glTexCoord2d(s * TexMaxS, t * TexMaxT)
                glVertex3d(x, y, z)
        glEnd()
        line0 = line1

def GenerateSpotMesh():
    global SpotMesh
    rx0 = SpotRadius * PixelX
    ry0 = SpotRadius * PixelY
    rx1 = (SpotRadius + BoxEdgeSize) * PixelX
    ry1 = (SpotRadius + BoxEdgeSize) * PixelY
    steps = max(6, int(2.0 * pi * SpotRadius / SpotDetail / ZoomArea))
    SpotMesh=[(rx0 * sin(a), ry0 * cos(a), rx1 * sin(a), ry1 * cos(a)) for a in \
             [i * 2.0 * pi / steps for i in range(steps + 1)]]


##### TRANSITIONS ##############################################################

# Each transition is represented by a class derived from impressive.Transition
# The interface consists of only two methods: the __init__ method may perform
# some transition-specific initialization, and render() finally renders a frame
# of the transition, using the global texture identifierst Tcurrent and Tnext.

# Transition itself is an abstract class
class AbstractError(StandardError):
    pass
class Transition:
    def __init__(self):
        pass
    def render(self, t):
        raise AbstractError

# an array containing all possible transition classes
AllTransitions=[]

# a helper function doing the common task of directly blitting a background page
def DrawPageDirect(tex):
    glDisable(GL_BLEND)
    glBindTexture(TextureTarget, tex)
    glColor3d(1, 1, 1)
    DrawFullQuad()

# a helper function that enables alpha blending
def EnableAlphaBlend():
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)


# Crossfade: one of the simplest transition you can think of :)
class Crossfade(Transition):
    """simple crossfade"""
    def render(self,t):
      DrawPageDirect(Tcurrent)
      EnableAlphaBlend()
      glBindTexture(TextureTarget, Tnext)
      glColor4d(1, 1, 1, t)
      DrawFullQuad()
AllTransitions.append(Crossfade)


# Slide: a class of transitions that simply slide the new page in from one side
# after an idea from Joachim B Haga
class Slide(Transition):
    def origin(self, t):
        raise AbstractError
    def render(self, t):
        cx, cy, nx, ny = self.origin(t)
    	glBindTexture(TextureTarget, Tcurrent)
    	DrawQuad(cx, cy, cx+1.0, cy+1.0)
    	glBindTexture(TextureTarget, Tnext)
    	DrawQuad(nx, ny, nx+1.0, ny+1.0)

class SlideLeft(Slide):
    """Slide to the left"""
    def origin(self, t): return (-t, 0.0, 1.0-t, 0.0)
class SlideRight(Slide):
    """Slide to the right"""
    def origin(self, t): return (t, 0.0, t-1.0, 0.0)
class SlideUp(Slide):
    """Slide upwards"""
    def origin(self, t): return (0.0, -t, 0.0, 1.0-t)
class SlideDown(Slide):
    """Slide downwards"""
    def origin(self, t): return (0.0, t, 0.0, t-1.0)
AllTransitions.extend([SlideLeft, SlideRight, SlideUp, SlideDown])


# Squeeze: a class of transitions that squeeze the new page in from one size
class Squeeze(Transition):
    def params(self, t):
        raise AbstractError
    def inv(self): return 0
    def render(self, t):
        cx1, cy1, nx0, ny0 = self.params(t)
        if self.inv():
            t1, t2 = (Tnext, Tcurrent)
        else:
            t1, t2 = (Tcurrent, Tnext)
    	glBindTexture(TextureTarget, t1)
    	DrawQuad(0.0, 0.0, cx1, cy1)
    	glBindTexture(TextureTarget, t2)
    	DrawQuad(nx0, ny0, 1.0, 1.0)
class SqueezeHorizontal(Squeeze):
    def split(self, t): raise AbstractError
    def params(self, t):
        t = self.split(t)
        return (t, 1.0, t, 0.0)
class SqueezeVertical(Squeeze):
    def split(self, t): raise AbstractError
    def params(self, t):
        t = self.split(t)
        return (1.0, t, 0.0, t)

class SqueezeLeft(SqueezeHorizontal):
    """Squeeze to the left"""
    def split(self, t): return 1.0 - t
class SqueezeRight(SqueezeHorizontal):
    """Squeeze to the right"""
    def split(self, t): return t
    def inv(self): return 1
class SqueezeUp(SqueezeVertical):
    """Squeeze upwards"""
    def split(self, t): return 1.0 - t
class SqueezeDown(SqueezeVertical):
    """Squeeze downwards"""
    def split(self, t): return t
    def inv(self): return 1
AllTransitions.extend([SqueezeLeft, SqueezeRight, SqueezeUp, SqueezeDown])


# Wipe: a class of transitions that softly "wipe" the new image over the old
# one along a path specified by a gradient function that maps normalized screen
# coordinates to a number in the range [0.0,1.0]
WipeWidth = 0.25
class Wipe(Transition):
    def grad(self, u, v):
        raise AbstractError
    def afunc(self, g):
        pos = (g - self.Wipe_start) / WipeWidth
        return max(min(pos, 1.0), 0.0)
    def render(self, t):
        DrawPageDirect(Tnext)
        EnableAlphaBlend()
        glBindTexture(TextureTarget, Tcurrent)
        self.Wipe_start = t * (1.0 + WipeWidth) - WipeWidth
        DrawMeshQuad(t, lambda t, u, v: \
                     (u, v, 0.0,  u,v,  1.0, self.afunc(self.grad(u, v))))

class WipeDown(Wipe):
    """wipe downwards"""
    def grad(self, u, v): return v
class WipeUp(Wipe):
    """wipe upwards"""
    def grad(self, u, v): return 1.0 - v
class WipeRight(Wipe):
    """wipe from left to right"""
    def grad(self, u, v): return u
class WipeLeft(Wipe):
    """wipe from right to left"""
    def grad(self, u, v): return 1.0 - u
class WipeDownRight(Wipe):
    """wipe from the upper-left to the lower-right corner"""
    def grad(self, u, v): return 0.5 * (u + v)
class WipeUpLeft(Wipe):
    """wipe from the lower-right to the upper-left corner"""
    def grad(self, u, v): return 1.0 - 0.5 * (u + v)
class WipeCenterOut(Wipe):
    """wipe from the center outwards"""
    def grad(self, u, v):
        u -= 0.5
        v -= 0.5
        return sqrt(u * u * 1.777 + v * v) / 0.833
class WipeCenterIn(Wipe):
    """wipe from the edges inwards"""
    def grad(self, u, v):
        u -= 0.5
        v -= 0.5
        return 1.0 - sqrt(u * u * 1.777 + v * v) / 0.833
AllTransitions.extend([WipeDown, WipeUp, WipeRight, WipeLeft, \
                       WipeDownRight, WipeUpLeft, WipeCenterOut, WipeCenterIn])

class WipeBlobs(Wipe):
    """wipe using nice \"blob\"-like patterns"""
    def __init__(self):
        self.uscale = (5.0 + random.random() * 15.0) * 1.333
        self.vscale =  5.0 + random.random() * 15.0
        self.uofs = random.random() * 6.2
        self.vofs = random.random() * 6.2
    def grad(self,u,v):
        return 0.5 + 0.25 * (cos(self.uofs + u * self.uscale) \
                          +  cos(self.vofs + v * self.vscale))
AllTransitions.append(WipeBlobs)

class PagePeel(Transition):
    """an unrealistic, but nice page peel effect"""
    def render(self,t):
        glDisable(GL_BLEND)
        glBindTexture(TextureTarget, Tnext)
        DrawMeshQuad(t, lambda t, u, v: \
                     (u, v, 0.0,  u, v,  1.0 - 0.5 * (1.0 - u) * (1.0 - t), 1.0))
        EnableAlphaBlend()
        glBindTexture(TextureTarget, Tcurrent)
        DrawMeshQuad(t, lambda t, u, v: \
                     (u * (1.0 - t), 0.5 + (v - 0.5) * (1.0 + u * t) * (1.0 + u * t), 0.0,
                      u, v,  1.0 - u * t * t, 1.0))
AllTransitions.append(PagePeel)

### additional transition by Ronan Le Hy <rlehy@free.fr> ###

class PageTurn(Transition):
    """another page peel effect, slower but more realistic than PagePeel"""
    alpha = 2.
    alpha_square = alpha * alpha
    sqrt_two = sqrt(2.)
    inv_sqrt_two = 1. / sqrt(2.)
    def warp(self, t, u, v):
        # distance from the 2d origin to the folding line
        dpt = PageTurn.sqrt_two * (1.0 - t)
        # distance from the 2d origin to the projection of (u,v) on the folding line
        d = PageTurn.inv_sqrt_two * (u + v)
        dmdpt = d - dpt
        # the smaller rho is, the closer to asymptotes are the x(u) and y(v) curves
        # ie, smaller rho => neater fold
        rho = 0.001
        common_sq = sqrt(4. - 8 * t - 4.*(u+v) + 4.*t*(t + v + u) + (u+v)*(u+v) + 4 * rho) / 2.
        x = 1. - t + 0.5 * (u - v) - common_sq
        y = 1. - t + 0.5 * (v - u) - common_sq
        z = - 0.5 * (PageTurn.alpha * dmdpt + sqrt(PageTurn.alpha_square * dmdpt*dmdpt + 4))
        if dmdpt < 0:
            # part of the sheet still flat on the screen: lit and opaque
            i = 1.0
            alpha = 1.0
        else:
            # part of the sheet in the air, after the fold: shadowed and transparent
            # z goes from -0.8 to -2 approximately
            i = -0.5 * z
            alpha = 0.5 * z + 1.5
            # the corner of the page that you hold between your fingers
            dthumb = 0.6 * u + 1.4 * v - 2 * 0.95
            if dthumb > 0:
                z -= dthumb
                x += dthumb
                y += dthumb
                i = 1.0
                alpha = 1.0
        return (x,y,z, u,v, i, alpha)
    def render(self, t):
        glDisable(GL_BLEND)
        glBindTexture(TextureTarget, Tnext)
        DrawMeshQuad(t,lambda t, u, v: \
                    (u, v, 0.0,  u, v,  1.0 - 0.5 * (1.0 - u) * (1.0 - t), 1.0))
        EnableAlphaBlend()
        glBindTexture(TextureTarget, Tcurrent)
        DrawMeshQuad(t, self.warp)
AllTransitions.append(PageTurn)

##### some additional transitions by Rob Reid <rreid@drao.nrc.ca> #####

class ZoomOutIn(Transition):
    """zooms the current page out, and the next one in."""
    def render(self, t):
        glColor3d(0.0, 0.0, 0.0)
        DrawFullQuad()
        if t < 0.5:
            glBindTexture(TextureTarget, Tcurrent)
            scalfact = 1.0 - 2.0 * t
            DrawMeshQuad(t, lambda t, u, v: (0.5 + scalfact * (u - 0.5), \
                                             0.5 + scalfact * (v - 0.5), 0.0, \
                                             u, v, 1.0, 1.0))
        else:
            glBindTexture(TextureTarget, Tnext)
            scalfact = 2.0 * t - 1.0
            EnableAlphaBlend()
            DrawMeshQuad(t, lambda t, u, v: (0.5 + scalfact * (u - 0.5), \
                                             0.5 + scalfact * (v - 0.5), 0.0, \
                                             u, v, 1.0, 1.0))
AllTransitions.append(ZoomOutIn)

class SpinOutIn(Transition):
    """spins the current page out, and the next one in."""
    def render(self, t):
        glColor3d(0.0, 0.0, 0.0)
        DrawFullQuad()
        if t < 0.5:
            glBindTexture(TextureTarget, Tcurrent)
            scalfact = 1.0 - 2.0 * t
        else:
            glBindTexture(TextureTarget, Tnext)
            scalfact = 2.0 * t - 1.0
        sa = scalfact * sin(16.0 * t)
        ca = scalfact * cos(16.0 * t)
        DrawMeshQuad(t,lambda t, u, v: (0.5 + ca * (u - 0.5) - 0.75 * sa * (v - 0.5),\
                                        0.5 + 1.333 * sa * (u - 0.5) + ca * (v - 0.5),\
                                        0.0, u, v, 1.0, 1.0))
AllTransitions.append(SpinOutIn)

class SpiralOutIn(Transition):
    """flushes the current page away to have the next one overflow"""
    def render(self, t):
        glColor3d(0.0, 0.0, 0.0)
        DrawFullQuad()
        if t < 0.5:
            glBindTexture(TextureTarget,Tcurrent)
            scalfact = 1.0 - 2.0 * t
        else:
          glBindTexture(TextureTarget,Tnext)
          scalfact = 2.0 * t - 1.0
        sa = scalfact * sin(16.0 * t)
        ca = scalfact * cos(16.0 * t)
        DrawMeshQuad(t, lambda t, u, v: (0.5 + sa + ca * (u - 0.5) - 0.75 * sa * (v - 0.5),\
                                         0.5 + ca + 1.333 * sa * (u - 0.5) + ca * (v - 0.5),\
                                         0.0, u, v, 1.0, 1.0))
AllTransitions.append(SpiralOutIn)

# the AvailableTransitions array contains a list of all transition classes that
# can be randomly assigned to pages
AvailableTransitions=[ # from coolest to lamest
    # PagePeel, # deactivated: too intrusive
    WipeBlobs,
    WipeCenterOut,WipeCenterIn,
    WipeDownRight,WipeUpLeft,WipeDown,WipeUp,WipeRight,WipeLeft,
    Crossfade
]


##### OSD FONT RENDERER ########################################################

# force a string or sequence of ordinals into a unicode string
def ForceUnicode(s, charset='iso8859-15'):
    if type(s) == types.UnicodeType:
        return s
    if type(s) == types.StringType:
        return unicode(s, charset, 'ignore')
    if type(s) in (types.TupleType, types.ListType):
        return u''.join(map(unichr, s))
    raise TypeError, "string argument not convertible to Unicode"

# search a system font path for a font file
def SearchFont(root, name):
    if not os.path.isdir(root):
        return None
    infix = ""
    fontfile = []
    while (len(infix) < 10) and (len(fontfile) != 1):
        fontfile = filter(os.path.isfile, glob.glob(root + infix + name))
        infix += "*/"
    if len(fontfile) != 1:
        return None
    else:
        return fontfile[0]

# load a system font
def LoadFont(dirs, name, size):
    # first try to load the font directly
    try:
        return ImageFont.truetype(name, size, encoding='unic')
    except:
        pass
    # no need to search further on Windows
    if os.name == 'nt':
        return None
    # start search for the font
    for dir in dirs:
        fontfile = SearchFont(dir + "/", name)
        if fontfile:
            try:
                return ImageFont.truetype(fontfile, size, encoding='unic')
            except:
                pass
    return None

# alignment constants
Left = 0
Right = 1
Center = 2
Down = 0
Up = 1
Auto = -1

# font renderer class
class GLFont:
    def __init__(self, width, height, name, size, search_path=[], default_charset='iso8859-15', extend=1, blur=1):
        self.width = width
        self.height = height
        self._i_extend = range(extend)
        self._i_blur = range(blur)
        self.feather = extend + blur + 1
        self.current_x = 0
        self.current_y = 0
        self.max_height = 0
        self.boxes = {}
        self.widths = {}
        self.line_height = 0
        self.default_charset = default_charset
        if type(name) == types.StringType:
            self.font = LoadFont(search_path, name, size)
        else:
            for check_name in name:
                self.font = LoadFont(search_path, check_name, size)
                if self.font: break
        if not self.font:
            raise IOError, "font file not found"
        self.img = Image.new('LA', (width, height))
        self.alpha = Image.new('L', (width, height))
        self.extend = ImageFilter.MaxFilter()
        self.blur = ImageFilter.Kernel((3, 3), [1,2,1,2,4,2,1,2,1])
        self.tex = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.tex)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        self.AddString(range(32, 128))

    def AddCharacter(self, c):
        w, h = self.font.getsize(c)
        self.line_height = max(self.line_height, h)
        size = (w + 2 * self.feather, h + 2 * self.feather)
        glyph = Image.new('L', size)
        draw = ImageDraw.Draw(glyph)
        draw.text((self.feather, self.feather), c, font=self.font, fill=255)
        del draw

        box = self.AllocateGlyphBox(*size)
        self.img.paste(glyph, (box.orig_x, box.orig_y))

        for i in self._i_extend: glyph = glyph.filter(self.extend)
        for i in self._i_blur:   glyph = glyph.filter(self.blur)
        self.alpha.paste(glyph, (box.orig_x, box.orig_y))

        self.boxes[c] = box
        self.widths[c] = w
        del glyph

    def AddString(self, s, charset=None, fail_silently=False):
        update_count = 0
        try:
            for c in ForceUnicode(s, self.GetCharset(charset)):
                if c in self.widths:
                    continue
                self.AddCharacter(c)
                update_count += 1
        except ValueError:
            if fail_silently:
                pass
            else:
                raise
        if not update_count: return
        self.img.putalpha(self.alpha)
        glBindTexture(GL_TEXTURE_2D, self.tex)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_LUMINANCE_ALPHA, \
                     self.width, self.height, 0, \
                     GL_LUMINANCE_ALPHA, GL_UNSIGNED_BYTE, self.img.tostring())

    def AllocateGlyphBox(self, w, h):
        if self.current_x + w > self.width:
            self.current_x = 0
            self.current_y += self.max_height
            self.max_height = 0
        if self.current_y + h > self.height:
            raise ValueError, "bitmap too small for all the glyphs"
        box = self.GlyphBox()
        box.orig_x = self.current_x
        box.orig_y = self.current_y
        box.size_x = w
        box.size_y = h
        box.x0 =  self.current_x      / float(self.width)
        box.y0 =  self.current_y      / float(self.height)
        box.x1 = (self.current_x + w) / float(self.width)
        box.y1 = (self.current_y + h) / float(self.height)
        box.dsx = w * PixelX
        box.dsy = h * PixelY
        self.current_x += w
        self.max_height = max(self.max_height, h)
        return box

    def GetCharset(self, charset=None):
        if charset: return charset
        return self.default_charset

    def SplitText(self, s, charset=None):
        return ForceUnicode(s, self.GetCharset(charset)).split(u'\n')

    def GetLineHeight(self):
        return self.line_height

    def GetTextWidth(self, s, charset=None):
        return max([self.GetTextWidthEx(line) for line in self.SplitText(s, charset)])

    def GetTextHeight(self, s, charset=None):
        return len(self.SplitText(s, charset)) * self.line_height

    def GetTextSize(self, s, charset=None):
        lines = self.SplitText(s, charset)
        return (max([self.GetTextWidthEx(line) for line in lines]), len(lines) * self.line_height)

    def GetTextWidthEx(self, u):
        if u: return sum([self.widths.get(c, 0) for c in u])
        else: return 0

    def GetTextHeightEx(self, u=[]):
        return self.line_height

    def AlignTextEx(self, x, u, align=Left):
        if not align: return x
        return x - (self.GetTextWidthEx(u) / align)

    def Draw(self, origin, text, charset=None, align=Left, color=(1.0, 1.0, 1.0), alpha=1.0, beveled=True):
        lines = self.SplitText(text, charset)
        x0, y0 = origin
        x0 -= self.feather
        y0 -= self.feather
        glEnable(GL_TEXTURE_2D)
        glEnable(GL_BLEND)
        glBindTexture(GL_TEXTURE_2D, self.tex)
        if beveled:
            glBlendFunc(GL_ZERO, GL_ONE_MINUS_SRC_ALPHA)
            glColor4d(0.0, 0.0, 0.0, alpha)
            self.DrawLinesEx(x0, y0, lines, align)
        glBlendFunc(GL_ONE, GL_ONE)
        glColor3d(color[0] * alpha, color[1] * alpha, color[2] * alpha)
        self.DrawLinesEx(x0, y0, lines, align)
        glDisable(GL_BLEND)
        glDisable(GL_TEXTURE_2D)

    def DrawLinesEx(self, x0, y, lines, align=Left):
        global PixelX, PixelY
        glBegin(GL_QUADS)
        for line in lines:
            sy = y * PixelY
            x = self.AlignTextEx(x0, line, align)
            for c in line:
                if not c in self.widths: continue
                self.boxes[c].render(x * PixelX, sy)
                x += self.widths[c]
            y += self.line_height
        glEnd()

    class GlyphBox:
        def render(self, sx=0.0, sy=0.0):
            glTexCoord2d(self.x0, self.y0); glVertex2d(sx,          sy)
            glTexCoord2d(self.x0, self.y1); glVertex2d(sx,          sy+self.dsy)
            glTexCoord2d(self.x1, self.y1); glVertex2d(sx+self.dsx, sy+self.dsy)
            glTexCoord2d(self.x1, self.y0); glVertex2d(sx+self.dsx, sy)

# high-level draw function
def DrawOSD(x, y, text, halign=Auto, valign=Auto, alpha=1.0):
    if not(OSDFont) or not(text) or (alpha <= 0.004): return
    if alpha > 1.0: alpha = 1.0
    if halign == Auto:
        if x < 0:
            x += ScreenWidth
            halign = Right
        else:
            halign = Left
    if valign == Auto:
        if y < 0:
            y += ScreenHeight
            valign = Up
        else:
            valign = Down
        if valign != Down:
            y -= OSDFont.GetLineHeight() / valign
    if TextureTarget != GL_TEXTURE_2D:
        glDisable(TextureTarget)
    OSDFont.Draw((x, y), text, align=halign, alpha=alpha)

# very high-level draw function
def DrawOSDEx(position, text, alpha_factor=1.0):
    xpos = position >> 1
    y = (1 - 2 * (position & 1)) * OSDMargin
    if xpos < 2:
        x = (1 - 2 * xpos) * OSDMargin
        halign = Auto
    else:
        x = ScreenWidth / 2
        halign = Center
    DrawOSD(x, y, text, halign, alpha = OSDAlpha * alpha_factor)


##### PDF PARSER ###############################################################

class PDFError(Exception):
    pass

class PDFref:
    def __init__(self, ref):
        self.ref = ref
    def __repr__(self):
        return "PDFref(%d)" % self.ref

re_pdfstring = re.compile(r'\(\)|\(.*?[^\\]\)')
pdfstringrepl = [("\\"+x[0], x[1:]) for x in "(( )) n\n r\r t\t".split(" ")]
def pdf_maskstring(s):
    s = s[1:-1]
    for a, b in pdfstringrepl:
        s = s.replace(a, b)
    return " <" + "".join(["%02X"%ord(c) for c in s]) + "> "
def pdf_mask_all_strings(s):
    return re_pdfstring.sub(lambda x: pdf_maskstring(x.group(0)), s)
def pdf_unmaskstring(s):
    return "".join([chr(int(s[i:i+2], 16)) for i in xrange(1, len(s)-1, 2)])

class PDFParser:
    def __init__(self, filename):
        self.f = file(filename, "rb")

        # find the first cross-reference table
        self.f.seek(0, 2)
        filesize = self.f.tell()
        self.f.seek(filesize - 128)
        trailer = self.f.read()
        i = trailer.rfind("startxref")
        if i < 0:
            raise PDFError, "cross-reference table offset missing"
        try:
            offset = int(trailer[i:].split("\n")[1].strip())
        except (IndexError, ValueError):
            raise PDFError, "malformed cross-reference table offset"

        # follow the trailer chain
        self.xref = {}
        while offset:
            newxref = self.xref
            self.xref, rootref, offset = self.parse_trailer(offset)
            self.xref.update(newxref)

        # scan the page tree
        self.obj2page = {}
        self.page2obj = {}
        self.annots = {}
        self.page_count = 0
        self.box = {}
        root = self.getobj(rootref, 'Catalog')
        try:
            self.scan_page_tree(root['Pages'].ref)
        except KeyError:
            raise PDFError, "root page tree node missing"

    def getline(self):
        while True:
            line = self.f.readline().strip()
            if line: return line

    def find_length(self, tokens, begin, end):
        level = 1
        for i in xrange(1, len(tokens)):
            if tokens[i] == begin:  level += 1
            if tokens[i] == end:    level -= 1
            if not level: break
        return i + 1

    def parse_tokens(self, tokens, want_list=False):
        res = []
        while tokens:
            t = tokens[0]
            v = t
            tlen = 1
            if (len(tokens) >= 3) and (tokens[2] == 'R'):
                v = PDFref(int(t))
                tlen = 3
            elif t == "<<":
                tlen = self.find_length(tokens, "<<", ">>")
                v = self.parse_tokens(tokens[1 : tlen - 1], True)
                v = dict(zip(v[::2], v[1::2]))
            elif t == "[":
                tlen = self.find_length(tokens, "[", "]")
                v = self.parse_tokens(tokens[1 : tlen - 1], True)
            elif not(t) or (t[0] == "null"):
                v = None
            elif (t[0] == '<') and (t[-1] == '>'):
                v = pdf_unmaskstring(t)
            elif t[0] == '/':
                v = t[1:]
            elif t == 'null':
                v = None
            else:
                try:
                    v = float(t)
                    v = int(t)
                except ValueError:
                    pass
            res.append(v)
            del tokens[:tlen]
        if want_list:
            return res
        if not res:
            return None
        if len(res) == 1:
            return res[0]
        return res

    def parse(self, data):
        data = pdf_mask_all_strings(data)
        data = data.replace("<<", " << ").replace("[", " [ ").replace("(", " (")
        data = data.replace(">>", " >> ").replace("]", " ] ").replace(")", ") ")
        data = data.replace("/", " /")
        return self.parse_tokens(filter(None, data.split()))

    def getobj(self, obj, force_type=None):
        offset = self.xref.get(obj, 0)
        if not offset:
            raise PDFError, "referenced non-existing PDF object"
        self.f.seek(offset)
        header = self.getline().split(None, 2)
        if (header[-1] != "obj") or (header[0] != str(obj)):
            raise PDFError, "object does not start where it's supposed to"
        data = []
        while True:
            line = self.getline()
            if line in ("endobj", "stream"): break
            data.append(line)
        data = self.parse(" ".join(data))
        if force_type:
            try:
                t = data['Type']
            except (KeyError, IndexError, ValueError):
                t = None
            if t != force_type:
                raise PDFError, "object does not match the intended type"
        return data

    def parse_xref_section(self, start, count):
        xref = {}
        for obj in xrange(start, start + count):
            line = self.getline()
            if line[-1] == 'f':
                xref[obj] = 0
            else:
                xref[obj] = int(line[:10], 10)
        return xref

    def parse_trailer(self, offset):
        self.f.seek(offset)
        xref = {}
        rootref = 0
        offset = 0
        if self.getline() != "xref":
            raise PDFError, "cross-reference table does not start where it's supposed to"
            return (xref, rootref, offset)   # no xref table found, abort
        # parse xref sections
        while True:
            line = self.getline()
            if line == "trailer": break
            start, count = map(int, line.split())
            xref.update(self.parse_xref_section(start, count))
        # parse trailer
        while True:
            line = self.getline()
            if line in ("startxref", "%%EOF"): break
            if line[0] != '/': continue
            parts = line[1:].split()
            if parts[0] == 'Prev':
                offset = int(parts[1])
            if parts[0] == 'Root':
                if (len(parts) != 4) or (parts[3] != 'R'):
                    raise PDFError, "root catalog entry is not a reference"
                rootref = int(parts[1])
        return (xref, rootref, offset)

    def scan_page_tree(self, obj, mbox=None, cbox=None):
        node = self.getobj(obj)
        if node['Type'] == 'Pages':
            for kid in node['Kids']:
                self.scan_page_tree(kid.ref, node.get('MediaBox', mbox), node.get('CropBox', cbox))
        else:
            page = self.page_count + 1
            self.page_count = page
            self.obj2page[obj] = page
            self.page2obj[page] = obj
            self.annots[page] = [a.ref for a in node.get('Annots', [])]
            self.box[page] = node.get('CropBox', cbox) or node.get('MediaBox', mbox)

    def dest2page(self, dest):
        if type(dest) != types.ListType:
            return dest
        elif dest[0].__class__ == PDFref:
            return self.obj2page.get(dest[0].ref, None)
        else:
            return dest[0]

    def get_href(self, obj):
        node = self.getobj(obj, 'Annot')
        if node['Subtype'] != 'Link': return None
        dest = None
        if 'Dest' in node:
            dest = self.dest2page(node['Dest'])
        elif 'A' in node:
            action = node['A']['S']
            if action == 'URI':
                dest = node['A'].get('URI', None)
            elif action == 'GoTo':
                dest = self.dest2page(node['A'].get('D', None))
        if dest:
            return tuple(node['Rect'] + [dest])

    def GetHyperlinks(self):
        res = {}
        for page in self.annots:
            a = filter(None, map(self.get_href, self.annots[page]))
            if a: res[page] = a
        return res


def AddHyperlink(page_offset, page, target, linkbox, pagebox):
    page += page_offset
    if type(target) == types.IntType:
        target += page_offset
    w = 1.0 / (pagebox[2] - pagebox[0])
    h = 1.0 / (pagebox[3] - pagebox[1])
    x0 = (linkbox[0] - pagebox[0]) * w
    y0 = (pagebox[3] - linkbox[3]) * h
    x1 = (linkbox[2] - pagebox[0]) * w
    y1 = (pagebox[3] - linkbox[1]) * h
    href = (0, target, x0, y0, x1, y1)
    if GetPageProp(page, '_href'):
        PageProps[page]['_href'].append(href)
    else:
        SetPageProp(page, '_href', [href])


def FixHyperlinks(page):
    if not(GetPageProp(page, '_box')) or not(GetPageProp(page, '_href')):
        return  # no hyperlinks or unknown page size
    bx0, by0, bx1, by1 = GetPageProp(page, '_box')
    bdx = bx1 - bx0
    bdy = by1 - by0
    href = []
    for fixed, target, x0, y0, x1, y1 in GetPageProp(page, '_href'):
        if fixed:
            href.append((1, target, x0, y0, x1, y1))
        else:
            href.append((1, target, \
                int(bx0 + bdx * x0), int(by0 + bdy * y0), \
                int(bx0 + bdx * x1), int(by0 + bdy * y1)))
    SetPageProp(page, '_href', href)


def ParsePDF(filename):
    try:
        assert 0 == spawn(os.P_WAIT, pdftkPath, \
                ["pdftk", FileNameEscape + filename + FileNameEscape, \
                 "output", FileNameEscape + TempFileName + ".pdf" + FileNameEscape,
                 "uncompress"])
    except OSError:
        print >>sys.stderr, "Note: pdftk not found, hyperlinks disabled."
        return
    except AssertionError:
        print >>sys.stderr, "Note: pdftk failed, hyperlinks disabled."
        return

    count = 0
    try:
        try:
            pdf = PDFParser(TempFileName + ".pdf")
            for page, annots in pdf.GetHyperlinks().iteritems():
                for page_offset in FileProps[filename]['offsets']:
                    for a in annots:
                        AddHyperlink(page_offset, page, a[4], a[:4], pdf.box[page])
                count += len(annots)
                FixHyperlinks(page)
            del pdf
            return count
        except IOError:
            print >>sys.stderr, "Note: file produced by pdftk not readable, hyperlinks disabled."
        except PDFError, e:
            print >>sys.stderr, "Note: error in file produced by pdftk, hyperlinks disabled."
            print >>sys.stderr, "      PDF parser error message:", e
    finally:
        try:
            os.remove(TempFileName + ".pdf")
        except OSError:
            pass


##### PAGE CACHE MANAGEMENT ####################################################

# helper class that allows PIL to write and read image files with an offset
class IOWrapper:
    def __init__(self, f, offset=0):
        self.f = f
        self.offset = offset
        self.f.seek(offset)
    def read(self, count=None):
        if count is None:
            return self.f.read()
        else:
            return self.f.read(count)
    def write(self, data):
        self.f.write(data)
    def seek(self, pos, whence=0):
        assert(whence in (0, 1))
        if whence:
            self.f.seek(pos, 1)
        else:
            self.f.seek(pos + self.offset)
    def tell(self):
        return self.f.tell() - self.offset

# generate a "magic number" that is used to identify persistent cache files
def UpdateCacheMagic():
    global CacheMagic
    pool = [PageCount, ScreenWidth, ScreenHeight, b2s(Scaling), b2s(Supersample), b2s(Rotation)]
    flist = list(FileProps.keys())
    flist.sort(lambda a,b: cmp(a.lower(), b.lower()))
    for f in flist:
        pool.append(f)
        pool.extend(list(GetFileProp(f, 'stat', [])))
    CacheMagic = md5.new("\0".join(map(str, pool))).hexdigest()

# set the persistent cache file position to the current end of the file
def UpdatePCachePos():
    global CacheFilePos
    CacheFile.seek(0, 2)
    CacheFilePos = CacheFile.tell()

# rewrite the header of the persistent cache
def WritePCacheHeader(reset=False):
    pages = ["%08x" % PageCache.get(page, 0) for page in range(1, PageCount+1)]
    CacheFile.seek(0)
    CacheFile.write(CacheMagic + "".join(pages))
    if reset:
        CacheFile.truncate()
    UpdatePCachePos()

# return an image from the persistent cache or None if none is available
def GetPCacheImage(page):
    if CacheMode != PersistentCache:
        return  # not applicable if persistent cache isn't used
    Lcache.acquire()
    try:
        if page in PageCache:
            img = Image.open(IOWrapper(CacheFile, PageCache[page]))
            img.load()
            return img
    finally:
        Lcache.release()

# returns an image from the non-persistent cache or None if none is available
def GetCacheImage(page):
    if CacheMode in (NoCache, PersistentCache):
        return  # not applicable in uncached or persistent-cache mode
    Lcache.acquire()
    try:
        if page in PageCache:
            if CacheMode == FileCache:
                CacheFile.seek(PageCache[page])
                return CacheFile.read(TexSize)
            else:
                return PageCache[page]
    finally:
        Lcache.release()

# adds an image to the persistent cache
def AddToPCache(page, img):
    if CacheMode != PersistentCache:
        return  # not applicable if persistent cache isn't used
    Lcache.acquire()
    try:
        if page in PageCache:
            return  # page is already cached and we can't update it safely
                    # -> stop here (the new image will be identical to the old
                    #    one anyway)
        img.save(IOWrapper(CacheFile, CacheFilePos), "ppm")
        PageCache[page] = CacheFilePos
        WritePCacheHeader()
    finally:
        Lcache.release()

# adds an image to the non-persistent cache
def AddToCache(page, data):
    global CacheFilePos
    if CacheMode in (NoCache, PersistentCache):
        return  # not applicable in uncached or persistent-cache mode
    Lcache.acquire()
    try:
        if CacheMode == FileCache:
            if not(page in PageCache):
                PageCache[page] = CacheFilePos
                CacheFilePos += len(data)
            CacheFile.seek(PageCache[page])
            CacheFile.write(data)
        else:
            PageCache[page] = data
    finally:
        Lcache.release()

# invalidates the whole cache
def InvalidateCache():
    global PageCache, CacheFilePos
    Lcache.acquire()
    try:
        PageCache = {}
        if CacheMode == PersistentCache:
            UpdateCacheMagic()
            WritePCacheHeader(True)
        else:
            CacheFilePos = 0
    finally:
        Lcache.release()

# initialize the persistent cache
def InitPCache():
    global CacheFile, CacheMode

    # try to open the pre-existing cache file
    try:
        CacheFile = file(CacheFileName, "rb+")
    except IOError:
        CacheFile = None

    # check the cache magic
    UpdateCacheMagic()
    if CacheFile and (CacheFile.read(32) != CacheMagic):
        print >>sys.stderr, "Cache file mismatch, recreating cache."
        CacheFile.close()
        CacheFile = None

    if CacheFile:
        # if the magic was valid, import cache data
        print >>sys.stderr, "Using already existing persistent cache file."
        for page in range(1, PageCount+1):
            offset = int(CacheFile.read(8), 16)
            if offset:
                PageCache[page] = offset
        UpdatePCachePos()
    else:
        # if the magic was invalid or the file didn't exist, (re-)create it
        try:
            CacheFile = file(CacheFileName, "wb+")
        except IOError:
            print >>sys.stderr, "Error: cannot write the persistent cache file (`%s')" % CacheFileName
            print >>sys.stderr, "Falling back to temporary file cache."
            CacheMode = FileCache
        WritePCacheHeader()


##### PAGE RENDERING ###########################################################

# generate a dummy image
def DummyPage():
    img = Image.new('RGB', (ScreenWidth, ScreenHeight))
    img.paste(LogoImage, ((ScreenWidth  - LogoImage.size[0]) / 2,
                          (ScreenHeight - LogoImage.size[1]) / 2))
    return img

# load a page from a PDF file
def RenderPDF(page, MayAdjustResolution, ZoomMode):
    global UseGhostScript
    UseGhostScriptOnce = False

    SourceFile = GetPageProp(page, '_file')
    Resolution = GetFileProp(SourceFile, 'res', 96)
    RealPage = GetPageProp(page, '_page')

    if Supersample and not(ZoomMode):
        UseRes = int(0.5 + Resolution) * Supersample
        AlphaBits = 1
    else:
        UseRes = int(0.5 + Resolution)
        AlphaBits = 4
    if ZoomMode:
        UseRes = 2 * UseRes

    # call pdftoppm to generate the page image
    if not UseGhostScript:
        renderer = "pdftoppm"
        try:
            assert 0 == spawn(os.P_WAIT, \
                pdftoppmPath, ["pdftoppm", "-q"] + [ \
                "-f", str(RealPage), "-l", str(RealPage),
                "-r", str(int(UseRes)),
                FileNameEscape + SourceFile + FileNameEscape,
                TempFileName])
            # determine output filename
            digits = GetFileProp(SourceFile, 'digits', 6)
            imgfile = TempFileName + ("-%%0%dd.ppm" % digits) % RealPage
            if not os.path.exists(imgfile):
                for digits in xrange(6, 0, -1):
                    imgfile = TempFileName + ("-%%0%dd.ppm" % digits) % RealPage
                    if os.path.exists(imgfile): break
                SetFileProp(SourceFile, 'digits', digits)
        except OSError, (errcode, errmsg):
            print >>sys.stderr, "Warning: Cannot start pdftoppm -", errmsg
            print >>sys.stderr, "Falling back to GhostScript (permanently)."
            UseGhostScript = True
        except AssertionError:
            print >>sys.stderr, "There was an error while rendering page %d" % page
            print >>sys.stderr, "Falling back to GhostScript for this page."
            UseGhostScriptOnce = True

    # fallback to GhostScript
    if UseGhostScript or UseGhostScriptOnce:
        imgfile = TempFileName + ".tif"
        renderer = "GhostScript"
        try:
            assert 0 == spawn(os.P_WAIT, \
                GhostScriptPath, ["gs", "-q"] + GhostScriptPlatformOptions + [ \
                "-dBATCH", "-dNOPAUSE", "-sDEVICE=tiff24nc", "-dUseCropBox",
                "-sOutputFile=" + imgfile, \
                "-dFirstPage=%d" % RealPage, "-dLastPage=%d" % RealPage,
                "-r%dx%d" % (UseRes, int(UseRes * PAR)), \
                "-dTextAlphaBits=%d" % AlphaBits, \
                "-dGraphicsAlphaBits=%s" % AlphaBits, \
                FileNameEscape + SourceFile + FileNameEscape])
        except OSError, (errcode, errmsg):
            print >>sys.stderr, "Error: Cannot start GhostScript -", errmsg
            return DummyPage()
        except AssertionError:
            print >>sys.stderr, "There was an error while rendering page %d" % page
            return DummyPage()

    # open the page image file with PIL
    try:
        img = Image.open(imgfile)
    except:
        print >>sys.stderr, "Error: %s produced an unreadable file (page %d)" % (renderer, page)
        return DummyPage()

    # try to delete the file again (this constantly fails on Win32 ...)
    try:
        os.remove(imgfile)
    except OSError:
        pass

    # apply rotation
    rot = GetPageProp(page, 'rotate')
    if rot is None:
        rot = Rotation
    if rot:
        img = img.rotate(90 * (4 - rot))

    # determine real display size (don't care for ZoomMode, DisplayWidth and
    # DisplayHeight are only used for Supersample and AdjustResolution anyway)
    if Supersample:
        DisplayWidth  = img.size[0] / Supersample
        DisplayHeight = img.size[1] / Supersample
    else:
        DisplayWidth  = img.size[0]
        DisplayHeight = img.size[1]

    # if the image size is strange, re-adjust the rendering resolution
    if MayAdjustResolution \
    and ((abs(ScreenWidth  - DisplayWidth)  > 4) \
    or   (abs(ScreenHeight - DisplayHeight) > 4)):
        newsize = ZoomToFit((DisplayWidth,DisplayHeight))
        NewResolution = newsize[0] * Resolution/DisplayWidth
        if abs(1.0 - NewResolution / Resolution) > 0.05:
            # only modify anything if the resolution deviation is large enough
            SetFileProp(SourceFile, 'res', NewResolution)
            return RenderPDF(page, False, ZoomMode)

    # downsample a supersampled image
    if Supersample and not(ZoomMode):
        return img.resize((DisplayWidth, DisplayHeight), Image.ANTIALIAS)

    return img


# load a page from an image file
def LoadImage(page, ZoomMode):
    # open the image file with PIL
    try:
        img = Image.open(GetPageProp(page, '_file'))
    except:
        print >>sys.stderr, "Image file `%s' is broken." % (FileList[page - 1])
        return DummyPage()

    # apply rotation
    rot = GetPageProp(page, 'rotate')
    if rot is None:
        rot = Rotation
    if rot:
        img = img.rotate(90 * (4 - rot))

    # determine destination size
    newsize = ZoomToFit(img.size)
    # don't scale if the source size is too close to the destination size
    if abs(newsize[0] - img.size[0]) < 2: newsize = img.size
    # don't scale if the source is smaller than the destination
    if not(Scaling) and (newsize > img.size): newsize = img.size
    # zoom up (if wanted)
    if ZoomMode: newsize=(2 * newsize[0], 2 * newsize[1])
    # skip processing if there was no change
    if newsize == img.size: return img

    # select a nice filter and resize the image
    if newsize > img.size:
      filter = Image.BICUBIC
    else:
      filter = Image.ANTIALIAS
    return img.resize(newsize, filter)


# render a page to an OpenGL texture
def PageImage(page, ZoomMode=False, RenderMode=False):
    global OverviewNeedUpdate
    EnableCacheRead = not(ZoomMode or RenderMode)
    EnableCacheWrite = EnableCacheRead and \
                       (page >= PageRangeStart) and (page <= PageRangeEnd)

    # check for the image in the cache
    if EnableCacheRead:
        data = GetCacheImage(page)
        if data: return data

    # if it's not in the temporary cache, render it
    Lrender.acquire()
    try:
        # retrieve the image from the persistent cache or fully re-render it
        if EnableCacheRead:
            img = GetPCacheImage(page)
        else:
            img = None
        if not img:
            if GetPageProp(page, '_page'):
                img = RenderPDF(page, not(ZoomMode), ZoomMode)
            else:
                img = LoadImage(page, ZoomMode)
            if EnableCacheWrite:
                AddToPCache(page, img)

        # create black background image to paste real image onto
        if ZoomMode:
            TextureImage = Image.new('RGB', (2 * TexWidth, 2 * TexHeight))
            TextureImage.paste(img, ((2 * ScreenWidth  - img.size[0]) / 2, \
                                     (2 * ScreenHeight - img.size[1]) / 2))
        else:
            TextureImage = Image.new('RGB', (TexWidth, TexHeight))
            x0 = (ScreenWidth  - img.size[0]) / 2
            y0 = (ScreenHeight - img.size[1]) / 2
            TextureImage.paste(img, (x0, y0))
            SetPageProp(page, '_box', (x0, y0, x0 + img.size[0], y0 + img.size[1]))
            FixHyperlinks(page)

        # paste thumbnail into overview image
        if GetPageProp(page, ('overview', '_overview'), True) \
        and (page >= PageRangeStart) and (page <= PageRangeEnd) \
        and not(GetPageProp(page, '_overview_rendered')) \
        and not(RenderMode):
            pos = OverviewPos(OverviewPageMapInv[page])
            Loverview.acquire()
            try:
                # first, fill the underlying area with black (i.e. remove the dummy logo)
                blackness = Image.new('RGB', (OverviewCellX - OverviewBorder, \
                                              OverviewCellY - OverviewBorder))
                OverviewImage.paste(blackness, (pos[0] + OverviewBorder / 2, \
                                                pos[1] + OverviewBorder))
                del blackness
                # then, scale down the original image and paste it
                img.thumbnail((OverviewCellX - 2 * OverviewBorder, \
                               OverviewCellY - 2 * OverviewBorder), \
                               Image.ANTIALIAS)
                OverviewImage.paste(img, \
                   (pos[0] + (OverviewCellX - img.size[0]) / 2, \
                    pos[1] + (OverviewCellY - img.size[1]) / 2))
            finally:
                Loverview.release()
            SetPageProp(page, '_overview_rendered', True)
            OverviewNeedUpdate = True
        del img

        # return texture data
        if RenderMode:
            return TextureImage
        data=TextureImage.tostring()
        del TextureImage
    finally:
      Lrender.release()

    # finally add it back into the cache and return it
    if EnableCacheWrite:
        AddToCache(page, data)
    return data

# render a page to an OpenGL texture
def RenderPage(page, target):
    glBindTexture(TextureTarget ,target)
    try:
        glTexImage2D(TextureTarget, 0, 3, TexWidth, TexHeight, 0,\
                     GL_RGB, GL_UNSIGNED_BYTE, PageImage(page))
    except GLerror:
        print >>sys.stderr, "I'm sorry, but your graphics card is not capable of rendering presentations"
        print >>sys.stderr, "in this resolution. Either the texture memory is exhausted, or there is no"
        print >>sys.stderr, "support for large textures (%dx%d). Please try to run Impressive in a" % (TexWidth, TexHeight)
        print >>sys.stderr, "smaller resolution using the -g command-line option."
        sys.exit(1)

# background rendering thread
def RenderThread(p1, p2):
    global RTrunning, RTrestart
    RTrunning = True
    RTrestart = True
    while RTrestart:
        RTrestart = False
        for pdf in FileProps:
            if not pdf.lower().endswith(".pdf"): continue
            if RTrestart: break
            ParsePDF(pdf)
        if RTrestart: continue
        for page in xrange(1, PageCount + 1):
            if RTrestart: break
            if (page != p1) and (page != p2) \
            and (page >= PageRangeStart) and (page <= PageRangeEnd):
                PageImage(page)
    RTrunning = False
    if CacheMode >= FileCache:
        print >>sys.stderr, "Background rendering finished, used %.1f MiB of disk space." %\
              (CacheFilePos / 1048576.0)


##### RENDER MODE ##############################################################

def DoRender():
    global TexWidth, TexHeight
    TexWidth = ScreenWidth
    TexHeight = ScreenHeight
    if os.path.exists(RenderToDirectory):
        print >>sys.stderr, "Destination directory `%s' already exists," % RenderToDirectory
        print >>sys.stderr, "refusing to overwrite anything."
        return 1
    try:
        os.mkdir(RenderToDirectory)
    except OSError, e:
        print >>sys.stderr, "Cannot create destination directory `%s':" % RenderToDirectory
        print >>sys.stderr, e.strerror
        return 1
    print >>sys.stderr, "Rendering presentation into `%s'" % RenderToDirectory
    for page in xrange(1, PageCount + 1):
        PageImage(page, RenderMode=True).save("%s/page%04d.png" % (RenderToDirectory, page))
        sys.stdout.write("[%d] " % page)
        sys.stdout.flush()
    print >>sys.stderr
    print >>sys.stderr, "Done."
    return 0


##### INFO SCRIPT I/O ##########################################################

# info script reader
def LoadInfoScript():
    global PageProps
    try:
        OldPageProps = PageProps
        execfile(InfoScriptPath, globals())
        NewPageProps = PageProps
        PageProps = OldPageProps
        del OldPageProps
        for page in NewPageProps:
            for prop in NewPageProps[page]:
                SetPageProp(page, prop, NewPageProps[page][prop])
        del NewPageProps
    except IOError:
        pass
    except:
        print >>sys.stderr, "----- Exception in info script ----"
        traceback.print_exc(file=sys.stderr)
        print >>sys.stderr, "----- End of traceback -----"

# we can't save lamba expressions, so we need to warn the user
# in every possible way
ScriptTainted = False
LambdaWarning = False
def here_was_a_lambda_expression_that_could_not_be_saved():
    global LambdaWarning
    if not LambdaWarning:
        print >>sys.stderr, "WARNING: The info script for the current file contained lambda expressions that"
        print >>sys.stderr, "         were removed during the a save operation."
        LambdaWarning = True

# "clean" a PageProps entry so that only 'public' properties are left
def GetPublicProps(props):
    props = props.copy()
    # delete private (underscore) props
    for prop in list(props.keys()):
        if str(prop)[0] == '_':
            del props[prop]
    # clean props to default values
    if props.get('overview', False):
        del props['overview']
    if not props.get('skip', True):
        del props['skip']
    if ('boxes' in props) and not(props['boxes']):
        del props['boxes']
    return props

# Generate a string representation of a property value. Mainly this converts
# classes or instances to the name of the class.
def PropValueRepr(value):
    global ScriptTainted
    if type(value) == types.FunctionType:
        if value.__name__ != "<lambda>":
            return value.__name__
        if not ScriptTainted:
            print >>sys.stderr, "WARNING: The info script contains lambda expressions, which cannot be saved"
            print >>sys.stderr, "         back. The modifed script will be written into a separate file to"
            print >>sys.stderr, "         minimize data loss."
            ScriptTainted = True
        return "here_was_a_lambda_expression_that_could_not_be_saved"
    elif type(value) == types.ClassType:
        return value.__name__
    elif type(value) == types.InstanceType:
        return value.__class__.__name__
    elif type(value) == types.DictType:
        return "{ " + ", ".join([PropValueRepr(k) + ": " + PropValueRepr(value[k]) for k in value]) + " }"
    else:
        return repr(value)

# generate a nicely formatted string representation of a page's properties
def SinglePagePropRepr(page):
    props = GetPublicProps(PageProps[page])
    if not props: return None
    return "\n%3d: {%s\n     }" % (page, \
        ",".join(["\n       " + repr(prop) + ": " + PropValueRepr(props[prop]) for prop in props]))

# generate a nicely formatted string representation of all page properties
def PagePropRepr():
    pages = PageProps.keys()
    pages.sort()
    return "PageProps = {%s\n}" % (",".join(filter(None, map(SinglePagePropRepr, pages))))

# count the characters of a python dictionary source code, correctly handling
# embedded strings and comments, and nested dictionaries
def CountDictChars(s, start=0):
    context = None
    level = 0
    for i in xrange(start, len(s)):
        c = s[i]
        if context is None:
            if c == '{': level += 1
            if c == '}': level -= 1
            if c == '#': context = '#'
            if c == '"': context = '"'
            if c == "'": context = "'"
        elif context[0] == "\\":
            context=context[1]
        elif context == '#':
            if c in "\r\n": context = None
        elif context == '"':
            if c == "\\": context = "\\\""
            if c == '"': context = None
        elif context == "'":
            if c == "\\": context = "\\'"
            if c == "'": context = None
        if level < 0: return i
    raise ValueError, "the dictionary never ends"

# modify and save a file's info script
def SaveInfoScript(filename):
    # read the old info script
    try:
        f = file(filename, "r")
        script = f.read()
        f.close()
    except IOError:
        script = ""
    if not script:
        script = "# -*- coding: iso-8859-1 -*-\n"

    # replace the PageProps of the old info script with the current ones
    try:
        m = re.search("^.*(PageProps)\s*=\s*(\{).*$", script,re.MULTILINE)
        if m:
            script = script[:m.start(1)] + PagePropRepr() + \
                     script[CountDictChars(script, m.end(2)) + 1 :]
        else:
            script += "\n" + PagePropRepr() + "\n"
    except (AttributeError, ValueError):
        pass

    if ScriptTainted:
        filename += ".modified"

    # write the script back
    try:
        f = file(filename, "w")
        f.write(script)
        f.close()
    except:
        print >>sys.stderr, "Oops! Could not write info script!"


##### OPENGL RENDERING #########################################################

# draw OSD overlays
def DrawOverlays():
    reltime = pygame.time.get_ticks() - StartTime
    if EstimatedDuration and (OverviewMode or GetPageProp(Pcurrent, 'progress', True)):
        rel = (0.001 * reltime) / EstimatedDuration
        x = int(ScreenWidth * rel)
        y = 1.0 - ProgressBarSize * PixelX
        a = min(255, max(0, x - ScreenWidth))
        b = min(255, max(0, x - ScreenWidth - 256))
        r = a
        g = 255 - b
        b = 0
        glDisable(TextureTarget)
        glDisable(GL_TEXTURE_2D)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glBegin(GL_QUADS)
        glColor4ub(r, g, b, 0)
        glVertex2d(0, y)
        glVertex2d(rel, y)
        glColor4ub(r, g, b, ProgressBarAlpha)
        glVertex2d(rel, 1.0)
        glVertex2d(0, 1.0)
        glEnd()
        glDisable(GL_BLEND)
    if WantStatus:
        DrawOSDEx(OSDStatusPos, CurrentOSDStatus)
    if TimeDisplay:
        t = reltime / 1000
        DrawOSDEx(OSDTimePos, FormatTime(t, MinutesOnly))
    if CurrentOSDComment and (OverviewMode or not(TransitionRunning)):
        DrawOSD(ScreenWidth/2, \
                ScreenHeight - 3*OSDMargin - FontSize, \
                CurrentOSDComment, Center, Up)
    if CursorImage and CursorVisible:
        x, y = pygame.mouse.get_pos()
        x -= CursorHotspot[0]
        y -= CursorHotspot[1]
        X0 = x * PixelX
        Y0 = y * PixelY
        X1 = X0 + CursorSX
        Y1 = Y0 + CursorSY
        glDisable(TextureTarget)
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, CursorTexture)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glColor4ub(255, 255, 255, 255)
        glBegin(GL_QUADS)
        glTexCoord2d(0.0,      0.0);       glVertex2d(X0, Y0)
        glTexCoord2d(CursorTX, 0.0);       glVertex2d(X1, Y0)
        glTexCoord2d(CursorTX, CursorTY);  glVertex2d(X1, Y1)
        glTexCoord2d(0.0,      CursorTY);  glVertex2d(X0, Y1)
        glEnd()
        glDisable(GL_BLEND)
        glDisable(GL_TEXTURE_2D)

# draw the complete image of the current page
def DrawCurrentPage(dark=1.0, do_flip=True):
    if VideoPlaying: return
    boxes = GetPageProp(Pcurrent, 'boxes')
    glClear(GL_COLOR_BUFFER_BIT)

    # pre-transform for zoom
    glLoadIdentity()
    glOrtho(ZoomX0, ZoomX0 + ZoomArea,  ZoomY0 + ZoomArea, ZoomY0,  -10.0, 10.0)

    # background layer -- the page's image, darkened if it has boxes
    glDisable(GL_BLEND)
    glEnable(TextureTarget)
    glBindTexture(TextureTarget, Tcurrent)
    if boxes or Tracing:
        light = 1.0 - 0.25 * dark
    else:
        light = 1.0
    glColor3d(light, light, light)
    DrawFullQuad()

    if boxes or Tracing:
        # alpha-blend the same image some times to blur it
        EnableAlphaBlend()
        DrawTranslatedFullQuad(+PixelX * ZoomArea, 0.0, light, dark / 2)
        DrawTranslatedFullQuad(-PixelX * ZoomArea, 0.0, light, dark / 3)
        DrawTranslatedFullQuad(0.0, +PixelY * ZoomArea, light, dark / 4)
        DrawTranslatedFullQuad(0.0, -PixelY * ZoomArea, light, dark / 5)

    if boxes:
        # draw outer box fade
        EnableAlphaBlend()
        for X0, Y0, X1, Y1 in boxes:
            glBegin(GL_QUAD_STRIP)
            DrawPointEx(X0, Y0, 1);  DrawPointEx(X0 - EdgeX, Y0 - EdgeY, 0)
            DrawPointEx(X1, Y0, 1);  DrawPointEx(X1 + EdgeX, Y0 - EdgeY, 0)
            DrawPointEx(X1, Y1, 1);  DrawPointEx(X1 + EdgeX, Y1 + EdgeY, 0)
            DrawPointEx(X0, Y1, 1);  DrawPointEx(X0 - EdgeX, Y1 + EdgeY, 0)
            DrawPointEx(X0, Y0, 1);  DrawPointEx(X0 - EdgeX, Y0 - EdgeY, 0)
            glEnd()

        # draw boxes
        glDisable(GL_BLEND)
        glBegin(GL_QUADS)
        for X0, Y0, X1, Y1 in boxes:
            DrawPoint(X0, Y0)
            DrawPoint(X1, Y0)
            DrawPoint(X1, Y1)
            DrawPoint(X0, Y1)
        glEnd()

    if Tracing:
        x, y = MouseToScreen(pygame.mouse.get_pos())
        # outer spot fade
        EnableAlphaBlend()
        glBegin(GL_TRIANGLE_STRIP)
        for x0, y0, x1, y1 in SpotMesh:
            DrawPointEx(x + x0, y + y0, 1)
            DrawPointEx(x + x1, y + y1, 0)
        glEnd()
        # inner spot
        glDisable(GL_BLEND)
        glBegin(GL_TRIANGLE_FAN)
        DrawPoint(x, y)
        for x0, y0, x1, y1 in SpotMesh:
            DrawPoint(x + x0, y + y0)
        glEnd()

    if Marking:
        # soft alpha-blended rectangle
        glDisable(TextureTarget)
        glColor4d(*MarkColor)
        EnableAlphaBlend()
        glBegin(GL_QUADS)
        glVertex2d(MarkUL[0], MarkUL[1])
        glVertex2d(MarkLR[0], MarkUL[1])
        glVertex2d(MarkLR[0], MarkLR[1])
        glVertex2d(MarkUL[0], MarkLR[1])
        glEnd()
        # bright red frame
        glDisable(GL_BLEND)
        glBegin(GL_LINE_STRIP)
        glVertex2d(MarkUL[0], MarkUL[1])
        glVertex2d(MarkLR[0], MarkUL[1])
        glVertex2d(MarkLR[0], MarkLR[1])
        glVertex2d(MarkUL[0], MarkLR[1])
        glVertex2d(MarkUL[0], MarkUL[1])
        glEnd()
        glEnable(TextureTarget)

    # unapply the zoom transform
    glLoadIdentity()
    glOrtho(0.0, 1.0,  1.0, 0.0,  -10.0, 10.0)

    # Done.
    DrawOverlays()
    if do_flip:
        pygame.display.flip()

# draw a black screen with the Impressive logo at the center
def DrawLogo():
    glClear(GL_COLOR_BUFFER_BIT)
    glColor3ub(255, 255, 255)
    if TextureTarget != GL_TEXTURE_2D:
        glDisable(TextureTarget)
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, LogoTexture)
    glBegin(GL_QUADS)
    glTexCoord2d(0, 0);  glVertex2d(0.5 - 128.0 / ScreenWidth, 0.5 - 32.0 / ScreenHeight)
    glTexCoord2d(1, 0);  glVertex2d(0.5 + 128.0 / ScreenWidth, 0.5 - 32.0 / ScreenHeight)
    glTexCoord2d(1, 1);  glVertex2d(0.5 + 128.0 / ScreenWidth, 0.5 + 32.0 / ScreenHeight)
    glTexCoord2d(0, 1);  glVertex2d(0.5 - 128.0 / ScreenWidth, 0.5 + 32.0 / ScreenHeight)
    glEnd()
    if OSDFont:
        OSDFont.Draw((ScreenWidth / 2, ScreenHeight / 2 + 48), \
                     __version__, align=Center, alpha=0.25)
    glDisable(GL_TEXTURE_2D)

# draw the prerender progress bar
def DrawProgress(position):
    glDisable(TextureTarget)
    x0 = 0.1
    x2 = 1.0 - x0
    x1 = position * x2 + (1.0 - position) * x0
    y1 = 0.9
    y0 = y1 - 16.0 / ScreenHeight
    glBegin(GL_QUADS)
    glColor3ub( 64,  64,  64);  glVertex2d(x0, y0);  glVertex2d(x2, y0)
    glColor3ub(128, 128, 128);  glVertex2d(x2, y1);  glVertex2d(x0, y1)
    glColor3ub( 64, 128, 255);  glVertex2d(x0, y0);  glVertex2d(x1, y0)
    glColor3ub(  8,  32, 128);  glVertex2d(x1, y1);  glVertex2d(x0, y1)
    glEnd()
    glEnable(TextureTarget)

# fade mode
def DrawFadeMode(intensity, alpha):
    if VideoPlaying: return
    DrawCurrentPage(do_flip=False)
    glDisable(TextureTarget)
    EnableAlphaBlend()
    glColor4d(intensity, intensity, intensity, alpha)
    DrawFullQuad()
    glEnable(TextureTarget)
    pygame.display.flip()

def FadeMode(intensity):
    t0 = pygame.time.get_ticks()
    while True:
        if pygame.event.get([KEYDOWN,MOUSEBUTTONUP]): break
        t = (pygame.time.get_ticks() - t0) * 1.0 / BlankFadeDuration
        if t >= 1.0: break
        DrawFadeMode(intensity, t)
    DrawFadeMode(intensity, 1.0)

    while True:
        event = pygame.event.wait()
        if event.type == QUIT:
            PageLeft()
            Quit()
        elif event.type == VIDEOEXPOSE:
            DrawFadeMode(intensity, 1.0)
        elif event.type == MOUSEBUTTONUP:
            break
        elif event.type == KEYDOWN:
            if event.unicode == u'q':
                pygame.event.post(pygame.event.Event(QUIT))
            else:
                break

    t0 = pygame.time.get_ticks()
    while True:
        if pygame.event.get([KEYDOWN,MOUSEBUTTONUP]): break
        t = (pygame.time.get_ticks() - t0) * 1.0 / BlankFadeDuration
        if t >= 1.0: break
        DrawFadeMode(intensity, 1.0 - t)
    DrawCurrentPage()

# gamma control
def SetGamma(new_gamma=None, new_black=None, force=False):
    global Gamma, BlackLevel
    if new_gamma is None: new_gamma = Gamma
    if new_gamma <  0.1:  new_gamma = 0.1
    if new_gamma > 10.0:  new_gamma = 10.0
    if new_black is None: new_black = BlackLevel
    if new_black <   0:   new_black = 0
    if new_black > 254:   new_black = 254
    if not(force) and (abs(Gamma - new_gamma) < 0.01) and (new_black == BlackLevel):
        return
    Gamma = new_gamma
    BlackLevel = new_black
    scale = 1.0 / (255 - BlackLevel)
    power = 1.0 / Gamma
    ramp = [int(65535.0 * ((max(0, x - BlackLevel) * scale) ** power)) for x in range(256)]
    return pygame.display.set_gamma_ramp(ramp, ramp, ramp)

# cursor image
def PrepareCustomCursor(cimg):
    global CursorTexture, CursorSX, CursorSY, CursorTX, CursorTY
    w, h = cimg.size
    tw, th = map(npot, cimg.size)
    if (tw > 256) or (th > 256):
        print >>sys.stderr, "Custom cursor is rediculously large, reverting to normal one."
        return False
    img = Image.new('RGBA', (tw, th))
    img.paste(cimg, (0, 0))
    CursorTexture = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, CursorTexture)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, tw, th, 0, GL_RGBA, GL_UNSIGNED_BYTE, img.tostring())
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
    CursorSX = w * PixelX
    CursorSY = h * PixelY
    CursorTX = w / float(tw)
    CursorTY = h / float(th)
    return True


##### CONTROL AND NAVIGATION ###################################################

# update the applications' title bar
def UpdateCaption(page=0, force=False):
    global CurrentCaption, CurrentOSDCaption, CurrentOSDPage, CurrentOSDStatus
    global CurrentOSDComment
    if (page == CurrentCaption) and not(force):
        return
    CurrentCaption = page
    caption = __title__
    if DocumentTitle:
        caption += " - " + DocumentTitle
    if page < 1:
        CurrentOSDCaption = ""
        CurrentOSDPage = ""
        CurrentOSDStatus = ""
        CurrentOSDComment = ""
        pygame.display.set_caption(caption, __title__)
        return
    CurrentOSDPage = "%d/%d" % (page, PageCount)
    caption = "%s (%s)" % (caption, CurrentOSDPage)
    title = GetPageProp(page, 'title') or GetPageProp(page, '_title')
    if title:
        caption += ": %s" % title
        CurrentOSDCaption = title
    else:
        CurrentOSDCaption = ""
    status = []
    if GetPageProp(page, 'skip', False):
        status.append("skipped: yes")
    if not GetPageProp(page, ('overview', '_overview'), True):
        status.append("on overview page: no")
    CurrentOSDStatus = ", ".join(status)
    CurrentOSDComment = GetPageProp(page, 'comment')
    pygame.display.set_caption(caption, __title__)

# get next/previous page
def GetNextPage(page, direction):
    try_page = page
    while True:
        try_page += direction
        if try_page == page:
            return 0  # tried all pages, but none found
        if Wrap:
            if try_page < 1: try_page = PageCount
            if try_page > PageCount: try_page = 1
        else:
            if try_page < 1 or try_page > PageCount:
                return 0  # start or end of presentation
        if not GetPageProp(try_page, 'skip', False):
            return try_page

# pre-load the following page into Pnext/Tnext
def PreloadNextPage(page):
    global Pnext, Tnext
    if (page < 1) or (page > PageCount):
        Pnext = 0
        return 0
    if page == Pnext:
        return 1
    RenderPage(page, Tnext)
    Pnext = page
    return 1

# perform box fading; the fade animation time is mapped through func()
def BoxFade(func):
    t0 = pygame.time.get_ticks()
    while 1:
        if pygame.event.get([KEYDOWN,MOUSEBUTTONUP]): break
        t = (pygame.time.get_ticks() - t0) * 1.0 / BoxFadeDuration
        if t >= 1.0: break
        DrawCurrentPage(func(t))
    DrawCurrentPage(func(1.0))
    return 0

# reset the timer
def ResetTimer():
    global StartTime, PageEnterTime
    if TimeTracking and not(FirstPage):
        print "--- timer was reset here ---"
    StartTime = pygame.time.get_ticks()
    PageEnterTime = 0

# start video playback
def PlayVideo(video):
    global MPlayerPID, VideoPlaying
    if not video: return
    StopMPlayer()
    try:
        MPlayerPID = spawn(os.P_NOWAIT, \
            MPlayerPath, [MPlayerPath, "-quiet",  \
            "-monitorpixelaspect", "1:1", "-autosync", "100"] + \
            MPlayerPlatformOptions + [ "-slave", \
            "-wid", str(pygame.display.get_wm_info()['window']), \
            FileNameEscape + video + FileNameEscape])
        if MPlayerColorKey:
            glClear(GL_COLOR_BUFFER_BIT)
            pygame.display.flip()
        VideoPlaying = True
    except OSError:
        MPlayerPID = 0

# called each time a page is entered
def PageEntered(update_time=True):
    global PageEnterTime, MPlayerPID, IsZoomed, WantStatus
    if update_time:
        PageEnterTime = pygame.time.get_ticks() - StartTime
    IsZoomed = False  # no, we don't have a pre-zoomed image right now
    WantStatus = False  # don't show status unless it's changed interactively
    timeout = AutoAdvance
    shown = GetPageProp(Pcurrent, '_shown', 0)
    if not shown:
        timeout = GetPageProp(Pcurrent, 'timeout', timeout)
        video = GetPageProp(Pcurrent, 'video')
        sound = GetPageProp(Pcurrent, 'sound')
        PlayVideo(video)
        if sound and not(video):
            StopMPlayer()
            try:
                MPlayerPID = spawn(os.P_NOWAIT, \
                    MPlayerPath, [MPlayerPath, "-quiet", "-really-quiet", \
                    FileNameEscape + sound + FileNameEscape])
            except OSError:
                MPlayerPID = 0
        SafeCall(GetPageProp(Pcurrent, 'OnEnterOnce'))
    SafeCall(GetPageProp(Pcurrent, 'OnEnter'))
    if timeout: pygame.time.set_timer(USEREVENT_PAGE_TIMEOUT, timeout)
    SetPageProp(Pcurrent, '_shown', shown + 1)

# called each time a page is left
def PageLeft(overview=False):
    global FirstPage, LastPage, WantStatus
    WantStatus = False
    if not overview:
        if GetTristatePageProp(Pcurrent, 'reset'):
            ResetTimer()
        FirstPage = False
        LastPage = Pcurrent
        if GetPageProp(Pcurrent, '_shown', 0) == 1:
            SafeCall(GetPageProp(Pcurrent, 'OnLeaveOnce'))
        SafeCall(GetPageProp(Pcurrent, 'OnLeave'))
    if TimeTracking:
        t1 = pygame.time.get_ticks() - StartTime
        dt = (t1 - PageEnterTime + 500) / 1000
        if overview:
            p = "over"
        else:
            p = "%4d" % Pcurrent
        print "%s%9s%9s%9s" % (p, FormatTime(dt), \
                                  FormatTime(PageEnterTime / 1000), \
                                  FormatTime(t1 / 1000))

# perform a transition to a specified page
def TransitionTo(page):
    global Pcurrent, Pnext, Tcurrent, Tnext
    global PageCount, Marking, Tracing, Panning, TransitionRunning

    # first, stop the auto-timer
    pygame.time.set_timer(USEREVENT_PAGE_TIMEOUT, 0)

    # invalid page? go away
    if not PreloadNextPage(page):
        return 0

    # notify that the page has been left
    PageLeft()

    # box fade-out
    if GetPageProp(Pcurrent, 'boxes') or Tracing:
        skip = BoxFade(lambda t: 1.0 - t)
    else:
        skip = 0

    # some housekeeping
    Marking = False
    Tracing = False
    UpdateCaption(page)

    # check if the transition is valid
    tpage = min(Pcurrent, Pnext)
    if 'transition' in PageProps[tpage]:
        tkey = 'transition'
    else:
        tkey = '_transition'
    trans = PageProps[tpage][tkey]
    if trans is None:
        transtime = 0
    else:
        transtime = GetPageProp(tpage, 'transtime', TransitionDuration)
        try:
            dummy = trans.__class__
        except AttributeError:
            # ah, gotcha! the transition is not yet intantiated!
            trans = trans()
            PageProps[tpage][tkey] = trans

    # backward motion? then swap page buffers now
    backward = (Pnext < Pcurrent)
    if backward:
        Pcurrent, Pnext = (Pnext, Pcurrent)
        Tcurrent, Tnext = (Tnext, Tcurrent)

    # transition animation
    if not(skip) and transtime:
        transtime = 1.0 / transtime
        TransitionRunning = True
        t0 = pygame.time.get_ticks()
        while not(VideoPlaying):
            if pygame.event.get([KEYDOWN,MOUSEBUTTONUP]):
                skip = 1
                break
            t = (pygame.time.get_ticks() - t0) * transtime
            if t >= 1.0: break
            if backward: t = 1.0 - t
            glEnable(TextureTarget)
            trans.render(t)
            DrawOverlays()
            pygame.display.flip()
        TransitionRunning = False

    # forward motion => swap page buffers now
    if not backward:
        Pcurrent, Pnext = (Pnext, Pcurrent)
        Tcurrent, Tnext = (Tnext, Tcurrent)

    # box fade-in
    if not(skip) and GetPageProp(Pcurrent, 'boxes'): BoxFade(lambda t: t)

    # finally update the screen and preload the next page
    DrawCurrentPage() # I do that twice because for some strange reason, the
    PageEntered()
    if not PreloadNextPage(GetNextPage(Pcurrent, 1)):
        PreloadNextPage(GetNextPage(Pcurrent, -1))
    return 1

# zoom mode animation
def ZoomAnimation(targetx, targety, func):
    global ZoomX0, ZoomY0, ZoomArea
    t0 = pygame.time.get_ticks()
    while True:
        if pygame.event.get([KEYDOWN,MOUSEBUTTONUP]): break
        t = (pygame.time.get_ticks() - t0)* 1.0 / ZoomDuration
        if t >= 1.0: break
        t = func(t)
        t = (2.0 - t) * t
        ZoomX0 = targetx * t
        ZoomY0 = targety * t
        ZoomArea = 1.0 - 0.5 * t
        DrawCurrentPage()
    t = func(1.0)
    ZoomX0 = targetx * t
    ZoomY0 = targety * t
    ZoomArea = 1.0 - 0.5 * t
    GenerateSpotMesh()
    DrawCurrentPage()

# enter zoom mode
def EnterZoomMode(targetx, targety):
    global ZoomMode, IsZoomed, ZoomWarningIssued
    ZoomAnimation(targetx, targety, lambda t: t)
    ZoomMode = True
    if TextureTarget != GL_TEXTURE_2D:
        if not ZoomWarningIssued:
            print >>sys.stderr, "Sorry, but I can't increase the detail level in zoom mode any further when"
            print >>sys.stderr, "GL_ARB_texture_rectangle is used. Please try running Impressive with the"
            print >>sys.stderr, "'-e' parameter. If a modern nVidia or ATI graphics card is used, a driver"
            print >>sys.stderr, "update may also fix the problem."
            ZoomWarningIssued = True
        return
    if not IsZoomed:
        glBindTexture(TextureTarget, Tcurrent)
        try:
            glTexImage2D(TextureTarget, 0, 3, TexWidth * 2, TexHeight * 2, 0, \
                         GL_RGB, GL_UNSIGNED_BYTE, PageImage(Pcurrent, True))
        except GLerror:
            if not ZoomWarningIssued:
                print >>sys.stderr, "Sorry, but I can't increase the detail level in zoom mode any further, because"
                print >>sys.stderr, "your OpenGL implementation does not support that. Either the texture memory is"
                print >>sys.stderr, "exhausted, or there is no support for large textures (%dx%d). If you really" % (TexWidth * 2, TexHeight * 2)
                print >>sys.stderr, "need high-res zooming, please try to run Impressive in a smaller resolution"
                print >>sys.stderr, "using the -g command-line option."
                ZoomWarningIssued = True
            return
        DrawCurrentPage()
        IsZoomed = True

# leave zoom mode (if enabled)
def LeaveZoomMode():
    global ZoomMode
    if not ZoomMode: return
    ZoomAnimation(ZoomX0, ZoomY0, lambda t: 1.0 - t)
    ZoomMode = False
    Panning = False

# increment/decrement spot radius
def IncrementSpotSize(delta):
    global SpotRadius
    if not Tracing:
        return
    SpotRadius = max(SpotRadius + delta, 8)
    GenerateSpotMesh()
    DrawCurrentPage()

# post-initialize the page transitions
def PrepareTransitions():
    Unspecified = 0xAFFED00F
    # STEP 1: randomly assign transitions where the user didn't specify them
    cnt = sum([1 for page in xrange(1, PageCount + 1) \
               if GetPageProp(page, 'transition', Unspecified) == Unspecified])
    newtrans = ((cnt / len(AvailableTransitions) + 1) * AvailableTransitions)[:cnt]
    random.shuffle(newtrans)
    for page in xrange(1, PageCount + 1):
        if GetPageProp(page, 'transition', Unspecified) == Unspecified:
            SetPageProp(page, '_transition', newtrans.pop())
    # STEP 2: instantiate transitions
    for page in PageProps:
        for key in ('transition', '_transition'):
            if not key in PageProps[page]:
                continue
            trans = PageProps[page][key]
            if trans is not None:
                PageProps[page][key] = trans()

# update timer values and screen timer
def TimerTick():
    global CurrentTime, ProgressBarPos
    redraw = False
    newtime = (pygame.time.get_ticks() - StartTime) * 0.001
    if EstimatedDuration:
        newpos = int(ScreenWidth * newtime / EstimatedDuration)
        if newpos != ProgressBarPos:
            redraw = True
        ProgressBarPos = newpos
    newtime = int(newtime)
    if TimeDisplay and (CurrentTime != newtime):
        redraw = True
    CurrentTime = newtime
    return redraw

# set cursor visibility
def SetCursor(visible):
    global CursorVisible
    CursorVisible = visible
    if not CursorImage:
        pygame.mouse.set_visible(visible)

# shortcut handling
def IsValidShortcutKey(key):
    return ((key >= K_a)  and (key <= K_z)) \
        or ((key >= K_0)  and (key <= K_9)) \
        or ((key >= K_F1) and (key <= K_F12))
def FindShortcut(shortcut):
    for page, props in PageProps.iteritems():
        try:
            check = props['shortcut']
            if type(check) != types.StringType:
                check = int(check)
            elif (len(check) > 1) and (check[0] in "Ff"):
                check = K_F1 - 1 + int(check[1:])
            else:
                check = ord(check.lower())
        except (KeyError, TypeError, ValueError):
            continue
        if check == shortcut:
            return page
    return None
def AssignShortcut(page, key):
    old_page = FindShortcut(key)
    if old_page:
        del PageProps[old_page]['shortcut']
    if key < 127:
        shortcut = chr(key)
    elif (key >= K_F1) and (key <= K_F15):
        shortcut = "F%d" % (key - K_F1 + 1)
    else:
        shortcut = int(key)
    SetPageProp(page, 'shortcut', shortcut)


##### OVERVIEW MODE ############################################################

def UpdateOverviewTexture():
    global OverviewNeedUpdate
    glBindTexture(TextureTarget, Tnext)
    Loverview.acquire()
    try:
        glTexImage2D(TextureTarget, 0, 3, TexWidth, TexHeight, 0, \
                     GL_RGB, GL_UNSIGNED_BYTE, OverviewImage.tostring())
    finally:
        Loverview.release()
    OverviewNeedUpdate = False

# draw the overview page
def DrawOverview():
    if VideoPlaying: return
    glClear(GL_COLOR_BUFFER_BIT)
    glDisable(GL_BLEND)
    glEnable(TextureTarget)
    glBindTexture(TextureTarget, Tnext)
    glColor3ub(192, 192, 192)
    DrawFullQuad()

    pos = OverviewPos(OverviewSelection)
    X0 = PixelX *  pos[0]
    Y0 = PixelY *  pos[1]
    X1 = PixelX * (pos[0] + OverviewCellX)
    Y1 = PixelY * (pos[1] + OverviewCellY)
    glColor3d(1.0, 1.0, 1.0)
    glBegin(GL_QUADS)
    DrawPoint(X0, Y0)
    DrawPoint(X1, Y0)
    DrawPoint(X1, Y1)
    DrawPoint(X0, Y1)
    glEnd()

    DrawOSDEx(OSDTitlePos,  CurrentOSDCaption)
    DrawOSDEx(OSDPagePos,   CurrentOSDPage)
    DrawOSDEx(OSDStatusPos, CurrentOSDStatus)
    DrawOverlays()
    pygame.display.flip()

# overview zoom effect, time mapped through func
def OverviewZoom(func):
    global TransitionRunning
    pos = OverviewPos(OverviewSelection)
    X0 = PixelX * (pos[0] + OverviewBorder)
    Y0 = PixelY * (pos[1] + OverviewBorder)
    X1 = PixelX * (pos[0] - OverviewBorder + OverviewCellX)
    Y1 = PixelY * (pos[1] - OverviewBorder + OverviewCellY)

    TransitionRunning = True
    t0 = pygame.time.get_ticks()
    while not(VideoPlaying):
        t = (pygame.time.get_ticks() - t0) * 1.0 / ZoomDuration
        if t >= 1.0: break
        t = func(t)
        t1 = t*t
        t = 1.0 - t1

        zoom = (t * (X1 - X0) + t1) / (X1 - X0)
        OX = zoom * (t * X0 - X0) - (zoom - 1.0) * t * X0
        OY = zoom * (t * Y0 - Y0) - (zoom - 1.0) * t * Y0
        OX = t * X0 - zoom * X0
        OY = t * Y0 - zoom * Y0

        glDisable(GL_BLEND)
        glEnable(TextureTarget)
        glBindTexture(TextureTarget, Tnext)
        glBegin(GL_QUADS)
        glColor3ub(192, 192, 192)
        glTexCoord2d(    0.0,     0.0);  glVertex2d(OX,        OY)
        glTexCoord2d(TexMaxS,     0.0);  glVertex2d(OX + zoom, OY)
        glTexCoord2d(TexMaxS, TexMaxT);  glVertex2d(OX + zoom, OY + zoom)
        glTexCoord2d(    0.0, TexMaxT);  glVertex2d(OX,        OY + zoom)
        glColor3ub(255, 255, 255)
        glTexCoord2d(X0 * TexMaxS, Y0 * TexMaxT);  glVertex2d(OX + X0*zoom, OY + Y0 * zoom)
        glTexCoord2d(X1 * TexMaxS, Y0 * TexMaxT);  glVertex2d(OX + X1*zoom, OY + Y0 * zoom)
        glTexCoord2d(X1 * TexMaxS, Y1 * TexMaxT);  glVertex2d(OX + X1*zoom, OY + Y1 * zoom)
        glTexCoord2d(X0 * TexMaxS, Y1 * TexMaxT);  glVertex2d(OX + X0*zoom, OY + Y1 * zoom)
        glEnd()

        EnableAlphaBlend()
        glBindTexture(TextureTarget, Tcurrent)
        glColor4d(1.0, 1.0, 1.0, 1.0 - t * t * t)
        glBegin(GL_QUADS)
        glTexCoord2d(    0.0,     0.0);  glVertex2d(t * X0,      t * Y0)
        glTexCoord2d(TexMaxS,     0.0);  glVertex2d(t * X1 + t1, t * Y0)
        glTexCoord2d(TexMaxS, TexMaxT);  glVertex2d(t * X1 + t1, t * Y1 + t1)
        glTexCoord2d(    0.0, TexMaxT);  glVertex2d(t * X0,      t * Y1 + t1)
        glEnd()

        DrawOSDEx(OSDTitlePos,  CurrentOSDCaption, alpha_factor=t)
        DrawOSDEx(OSDPagePos,   CurrentOSDPage,    alpha_factor=t)
        DrawOSDEx(OSDStatusPos, CurrentOSDStatus,  alpha_factor=t)
        DrawOverlays()
        pygame.display.flip()
    TransitionRunning = False

# overview keyboard navigation
def OverviewKeyboardNav(delta):
    global OverviewSelection
    dest = OverviewSelection + delta
    if (dest >= OverviewPageCount) or (dest < 0):
        return
    OverviewSelection = dest
    x, y = OverviewPos(OverviewSelection)
    pygame.mouse.set_pos((x + (OverviewCellX / 2), y + (OverviewCellY / 2)))

# overview mode PageProp toggle
def OverviewTogglePageProp(prop, default):
    if (OverviewSelection < 0) or (OverviewSelection >= len(OverviewPageMap)):
        return
    page = OverviewPageMap[OverviewSelection]
    SetPageProp(page, prop, not(GetPageProp(page, prop, default)))
    UpdateCaption(page, force=True)
    DrawOverview()

# overview event handler
def HandleOverviewEvent(event):
    global OverviewSelection, TimeDisplay

    if event.type == QUIT:
        PageLeft(overview=True)
        Quit()
    elif event.type == VIDEOEXPOSE:
        DrawOverview()

    elif event.type == KEYDOWN:
        if (event.key == K_ESCAPE) or (event.unicode == u'q'):
            pygame.event.post(pygame.event.Event(QUIT))
        elif event.unicode == u'f':
            SetFullscreen(not Fullscreen)
        elif event.unicode == u't':
            TimeDisplay = not(TimeDisplay)
            DrawOverview()
        elif event.unicode == u'r':
            ResetTimer()
            if TimeDisplay: DrawOverview()
        elif event.unicode == u's':
            SaveInfoScript(InfoScriptPath)
        elif event.unicode == u'o':
            OverviewTogglePageProp('overview', GetPageProp(Pcurrent, '_overview', True))
        elif event.unicode == u'i':
            OverviewTogglePageProp('skip', False)
        elif event.key == K_UP:    OverviewKeyboardNav(-OverviewGridSize)
        elif event.key == K_LEFT:  OverviewKeyboardNav(-1)
        elif event.key == K_RIGHT: OverviewKeyboardNav(+1)
        elif event.key == K_DOWN:  OverviewKeyboardNav(+OverviewGridSize)
        elif event.key == K_TAB:
            OverviewSelection = -1
            return 0
        elif event.key in (K_RETURN, K_KP_ENTER):
            return 0
        elif IsValidShortcutKey(event.key):
            if event.mod & KMOD_SHIFT:
                try:
                    AssignShortcut(OverviewPageMap[OverviewSelection], event.key)
                except IndexError:
                    pass   # no valid page selected
            else:
                # load shortcut
                page = FindShortcut(event.key)
                if page:
                    OverviewSelection = OverviewPageMapInv[page]
                    x, y = OverviewPos(OverviewSelection)
                    pygame.mouse.set_pos((x + (OverviewCellX / 2), \
                                          y + (OverviewCellY / 2)))
                    DrawOverview()

    elif event.type == MOUSEBUTTONUP:
        if event.button == 1:
            return 0
        elif event.button in (2, 3):
            OverviewSelection = -1
            return 0

    elif event.type == MOUSEMOTION:
        pygame.event.clear(MOUSEMOTION)
        # mouse move in fullscreen mode -> show mouse cursor and reset mouse timer
        if Fullscreen:
            pygame.time.set_timer(USEREVENT_HIDE_MOUSE, MouseHideDelay)
            SetCursor(True)
        # determine highlighted page
        OverviewSelection = \
             int((event.pos[0] - OverviewOfsX) / OverviewCellX) + \
             int((event.pos[1] - OverviewOfsY) / OverviewCellY) * OverviewGridSize
        if (OverviewSelection < 0) or (OverviewSelection >= len(OverviewPageMap)):
            UpdateCaption(0)
        else:
            UpdateCaption(OverviewPageMap[OverviewSelection])
        DrawOverview()

    elif event.type == USEREVENT_HIDE_MOUSE:
        # mouse timer event -> hide fullscreen cursor
        pygame.time.set_timer(USEREVENT_HIDE_MOUSE, 0)
        SetCursor(False)
        DrawOverview()

    return 1

# overview mode entry/loop/exit function
def DoOverview():
    global Pcurrent, Pnext, Tcurrent, Tnext, Tracing, OverviewSelection
    global PageEnterTime, OverviewMode

    pygame.time.set_timer(USEREVENT_PAGE_TIMEOUT, 0)
    PageLeft()
    UpdateOverviewTexture()

    if GetPageProp(Pcurrent, 'boxes') or Tracing:
        BoxFade(lambda t: 1.0 - t)
    Tracing = False
    OverviewSelection = OverviewPageMapInv[Pcurrent]

    OverviewMode = True
    OverviewZoom(lambda t: 1.0 - t)
    DrawOverview()
    PageEnterTime = pygame.time.get_ticks() - StartTime
    while True:
        event = pygame.event.poll()
        if event.type == NOEVENT:
            force_update = OverviewNeedUpdate
            if OverviewNeedUpdate:
                UpdateOverviewTexture()
            if TimerTick() or force_update:
                DrawOverview()
            pygame.time.wait(20)
        elif not HandleOverviewEvent(event):
            break
    PageLeft(overview=True)

    if (OverviewSelection < 0) or (OverviewSelection >= OverviewPageCount):
        OverviewSelection = OverviewPageMapInv[Pcurrent]
        Pnext = Pcurrent
    else:
        Pnext = OverviewPageMap[OverviewSelection]
    if Pnext != Pcurrent:
        Pcurrent = Pnext
        RenderPage(Pcurrent, Tcurrent)
    UpdateCaption(Pcurrent)
    OverviewZoom(lambda t: t)
    OverviewMode = False
    DrawCurrentPage()

    if GetPageProp(Pcurrent, 'boxes'):
        BoxFade(lambda t: t)
    PageEntered()
    if not PreloadNextPage(GetNextPage(Pcurrent, 1)):
        PreloadNextPage(GetNextPage(Pcurrent, -1))


##### EVENT HANDLING ###########################################################

# set fullscreen mode
def SetFullscreen(fs, do_init=True):
    global Fullscreen

    # let pygame do the real work
    if do_init:
        if fs == Fullscreen: return
        if not pygame.display.toggle_fullscreen(): return
    Fullscreen=fs

    # redraw the current page (pygame is too lazy to send an expose event ...)
    DrawCurrentPage()

    # show cursor and set auto-hide timer
    if fs:
        pygame.time.set_timer(USEREVENT_HIDE_MOUSE, MouseHideDelay)
    else:
        pygame.time.set_timer(USEREVENT_HIDE_MOUSE, 0)
        SetCursor(True)

# PageProp toggle
def TogglePageProp(prop, default):
    global WantStatus
    SetPageProp(Pcurrent, prop, not(GetPageProp(Pcurrent, prop, default)))
    UpdateCaption(Pcurrent, force=True)
    WantStatus = True
    DrawCurrentPage()

# main event handling function
def HandleEvent(event):
    global HaveMark, ZoomMode, Marking, Tracing, Panning, SpotRadius, FileStats
    global MarkUL, MarkLR, MouseDownX, MouseDownY, PanAnchorX, PanAnchorY
    global ZoomX0, ZoomY0, RTrunning, RTrestart, StartTime, PageEnterTime
    global CurrentTime, TimeDisplay, TimeTracking, ProgressBarPos

    if event.type == QUIT:
        PageLeft()
        Quit()
    elif event.type == VIDEOEXPOSE:
        DrawCurrentPage()

    elif event.type == KEYDOWN:
        if VideoPlaying:
            StopMPlayer()
            DrawCurrentPage()
        elif (event.key == K_ESCAPE) or (event.unicode == u'q'):
            pygame.event.post(pygame.event.Event(QUIT))
        elif event.unicode == u'f':
            SetFullscreen(not Fullscreen)
        elif (event.key == K_TAB) and (event.mod & KMOD_ALT) and Fullscreen:
            SetFullscreen(False)
        elif event.unicode == u's':
            SaveInfoScript(InfoScriptPath)
        elif event.unicode == u'z':  # handle QWERTY and QWERTZ keyboards
            if ZoomMode:
                LeaveZoomMode()
            else:
                tx, ty = MouseToScreen(pygame.mouse.get_pos())
                EnterZoomMode(0.5 * tx, 0.5 * ty)
        elif event.unicode == u'b':
            FadeMode(0.0)
        elif event.unicode == u'w':
            FadeMode(1.0)
        elif event.unicode == u't':
            TimeDisplay = not(TimeDisplay)
            DrawCurrentPage()
            if TimeDisplay and not(TimeTracking) and FirstPage:
                print >>sys.stderr, "Time tracking mode enabled."
                TimeTracking = True
                print "page duration    enter    leave"
                print "---- -------- -------- --------"
        elif event.unicode == u'r':
            ResetTimer()
            if TimeDisplay: DrawCurrentPage()
        elif event.unicode == u'l':
            TransitionTo(LastPage)
        elif event.unicode == u'o':
            TogglePageProp('overview', GetPageProp(Pcurrent, '_overview', True))
        elif event.unicode == u'i':
            TogglePageProp('skip', False)
        elif event.key == K_TAB:
            LeaveZoomMode()
            DoOverview()
        elif event.key in (32, K_DOWN, K_RIGHT, K_PAGEDOWN):
            LeaveZoomMode()
            TransitionTo(GetNextPage(Pcurrent, 1))
        elif event.key in (K_BACKSPACE, K_UP, K_LEFT, K_PAGEUP):
            LeaveZoomMode()
            TransitionTo(GetNextPage(Pcurrent, -1))
        elif event.key == K_HOME:
            if Pcurrent != 1:
                TransitionTo(1)
        elif event.key == K_END:
            if Pcurrent != PageCount:
                TransitionTo(PageCount)
        elif event.key in (K_RETURN, K_KP_ENTER):
            if not(GetPageProp(Pcurrent, 'boxes')) and Tracing:
                BoxFade(lambda t: 1.0 - t)
            Tracing = not(Tracing)
            if not(GetPageProp(Pcurrent, 'boxes')) and Tracing:
                BoxFade(lambda t: t)
        elif event.unicode == u'+':
            IncrementSpotSize(+8)
        elif event.unicode == u'-':
            IncrementSpotSize(-8)
        elif event.unicode == u'[':
            SetGamma(new_gamma=Gamma / GammaStep)
        elif event.unicode == u']':
            SetGamma(new_gamma=Gamma * GammaStep)
        elif event.unicode == u'{':
            SetGamma(new_black=BlackLevel - BlackLevelStep)
        elif event.unicode == u'}':
            SetGamma(new_black=BlackLevel + BlackLevelStep)
        elif event.unicode == u'\\':
            SetGamma(1.0, 0)
        else:
            keyfunc = GetPageProp(Pcurrent, 'keys', {}).get(event.unicode, None)
            if keyfunc:
                SafeCall(keyfunc)
            elif IsValidShortcutKey(event.key):
                if event.mod & KMOD_SHIFT:
                    AssignShortcut(Pcurrent, event.key)
                else:
                    # load keyboard shortcut
                    page = FindShortcut(event.key)
                    if page and (page != Pcurrent):
                        TransitionTo(page)

    elif event.type == MOUSEBUTTONDOWN:
        if VideoPlaying:
            Marking = False
            Panning = False
            return
        MouseDownX, MouseDownY = event.pos
        if event.button == 1:
            MarkUL = MarkLR = MouseToScreen(event.pos)
        elif (event.button == 3) and ZoomMode:
            PanAnchorX = ZoomX0
            PanAnchorY = ZoomY0
        elif event.button == 4:
            IncrementSpotSize(+8)
        elif event.button == 5:
            IncrementSpotSize(-8)

    elif event.type == MOUSEBUTTONUP:
        if VideoPlaying:
            StopMPlayer()
            DrawCurrentPage()
            Marking = False
            Panning = False
            return
        if event.button == 2:
            LeaveZoomMode()
            DoOverview()
            return
        if event.button == 1:
            if Marking:
                # left mouse button released in marking mode -> stop box marking
                Marking = False
                # reject too small boxes
                if  (abs(MarkUL[0] - MarkLR[0]) > 0.04) \
                and (abs(MarkUL[1] - MarkLR[1]) > 0.03):
                    boxes = GetPageProp(Pcurrent, 'boxes', [])
                    oldboxcount = len(boxes)
                    boxes.append(NormalizeRect(MarkUL[0], MarkUL[1], MarkLR[0], MarkLR[1]))
                    SetPageProp(Pcurrent, 'boxes', boxes)
                    if not(oldboxcount) and not(Tracing):
                        BoxFade(lambda t: t)
                DrawCurrentPage()
            else:
                # left mouse button released, but no marking
                LeaveZoomMode()
                dest = GetNextPage(Pcurrent, 1)
                x, y = event.pos
                for valid, target, x0, y0, x1, y1 in GetPageProp(Pcurrent, '_href', []):
                    if valid and (x >= x0) and (x < x1) and (y >= y0) and (y < y1):
                        dest = target
                        break
                if type(dest) == types.IntType:
                    TransitionTo(dest)
                else:
                    RunURL(dest)
        if (event.button == 3) and not(Panning):
            # right mouse button -> check if a box has to be killed
            boxes = GetPageProp(Pcurrent, 'boxes', [])
            x, y = MouseToScreen(event.pos)
            try:
                # if a box is already present around the clicked position, kill it
                idx = FindBox(x, y, boxes)
                if (len(boxes) == 1) and not(Tracing):
                    BoxFade(lambda t: 1.0 - t)
                del boxes[idx]
                SetPageProp(Pcurrent, 'boxes', boxes)
                DrawCurrentPage()
            except ValueError:
                # no box present -> go to previous page
                LeaveZoomMode()
                TransitionTo(GetNextPage(Pcurrent, -1))
        Panning = False

    elif event.type == MOUSEMOTION:
        pygame.event.clear(MOUSEMOTION)
        # mouse move in fullscreen mode -> show mouse cursor and reset mouse timer
        if Fullscreen:
            pygame.time.set_timer(USEREVENT_HIDE_MOUSE, MouseHideDelay)
            SetCursor(True)
        # don't react on mouse input during video playback
        if VideoPlaying: return
        # activate marking if mouse is moved away far enough
        if event.buttons[0] and not(Marking):
            x, y = event.pos
            if (abs(x - MouseDownX) > 4) and (abs(y - MouseDownY) > 4):
                Marking = True
        # mouse move while marking -> update marking box
        if Marking:
            MarkLR = MouseToScreen(event.pos)
        # mouse move while RMB is pressed -> panning
        if event.buttons[2] and ZoomMode:
            x, y = event.pos
            if not(Panning) and (abs(x - MouseDownX) > 4) and (abs(y - MouseDownY) > 4):
                Panning = True
            ZoomX0 = PanAnchorX + (MouseDownX - x) * ZoomArea / ScreenWidth
            ZoomY0 = PanAnchorY + (MouseDownY - y) * ZoomArea / ScreenHeight
            ZoomX0 = min(max(ZoomX0, 0.0), 1.0 - ZoomArea)
            ZoomY0 = min(max(ZoomY0, 0.0), 1.0 - ZoomArea)
        # if anything changed, redraw the page
        if Marking or Tracing or event.buttons[2] or (CursorImage and CursorVisible):
            DrawCurrentPage()

    elif event.type == USEREVENT_HIDE_MOUSE:
        # mouse timer event -> hide fullscreen cursor
        pygame.time.set_timer(USEREVENT_HIDE_MOUSE, 0)
        SetCursor(False)
        DrawCurrentPage()

    elif event.type == USEREVENT_PAGE_TIMEOUT:
        TransitionTo(GetNextPage(Pcurrent, 1))

    elif event.type == USEREVENT_POLL_FILE:
        dirty = False
        for f in FileProps:
            if my_stat(f) != GetFileProp(f, 'stat'):
                dirty = True
                break
        if dirty:
            # first, check if the new file is valid
            if not os.path.isfile(GetPageProp(Pcurrent, '_file')):
                return
            # invalidate everything we used to know about the input files
            InvalidateCache()
            for props in PageProps.itervalues():
                for prop in ('_overview_rendered', '_box', '_href'):
                    if prop in props: del props[prop]
            LoadInfoScript()
            # force a transition to the current page, reloading it
            Pnext=-1
            TransitionTo(Pcurrent)
            # restart the background renderer thread. this is not completely safe,
            # i.e. there's a small chance that we fail to restart the thread, but
            # this isn't critical
            if CacheMode and BackgroundRendering:
                if RTrunning:
                    RTrestart = True
                else:
                    RTrunning = True
                    thread.start_new_thread(RenderThread, (Pcurrent, Pnext))

    elif event.type == USEREVENT_TIMER_UPDATE:
        if TimerTick():
            DrawCurrentPage()


##### FILE LIST GENERATION #####################################################

def IsImageFileName(name):
    return os.path.splitext(name)[1].lower() in \
           (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".ppm", ".pgm")
def IsPlayable(name):
    return IsImageFileName(name) or name.lower().endswith(".pdf") or os.path.isdir(name)

def AddFile(name, title=None):
    global FileList, FileName

    if os.path.isfile(name):
        FileList.append(name)
        if title: SetFileProp(name, 'title', title)

    elif os.path.isdir(name):
        images = [os.path.join(name, f) for f in os.listdir(name) if IsImageFileName(f)]
        images.sort(lambda a, b: cmp(a.lower(), b.lower()))
        if not images:
            print >>sys.stderr, "Warning: no image files in directory `%s'" % name
        for img in images: AddFile(img)

    elif name.startswith('@') and os.path.isfile(name[1:]):
        name = name[1:]
        dirname = os.path.dirname(name)
        try:
            f = file(name, "r")
            next_title = None
            for line in f:
                line = [part.strip() for part in line.split('#', 1)]
                if len(line) == 1:
                    subfile = line[0]
                    title = None
                else:
                    subfile, title = line
                if subfile:
                    AddFile(os.path.normpath(os.path.join(dirname, subfile)), title)
            f.close()
        except IOError:
            print >>sys.stderr, "Error: cannot read list file `%s'" % name
        if not FileName:
            FileName = name
        else:
            FileName = ""

    else:
        files = list(filter(IsPlayable, glob.glob(name)))
        if files:
            for f in files: AddFile(f)
        else:
            print >>sys.stderr, "Error: input file `%s' not found" % name


##### INITIALIZATION ###########################################################

def main():
    global ScreenWidth, ScreenHeight, TexWidth, TexHeight, TexSize, LogoImage
    global TexMaxS, TexMaxT, MeshStepX, MeshStepY, EdgeX, EdgeY, PixelX, PixelY
    global OverviewGridSize, OverviewCellX, OverviewCellY
    global OverviewOfsX, OverviewOfsY, OverviewImage, OverviewPageCount
    global OverviewPageMap, OverviewPageMapInv, FileName, FileList, PageCount
    global DocumentTitle, PageProps, LogoTexture, OSDFont
    global Pcurrent, Pnext, Tcurrent, Tnext, InitialPage
    global CacheFile, CacheFileName
    global Extensions, AllowExtensions, TextureTarget, PAR, DAR, TempFileName
    global BackgroundRendering, FileStats, RTrunning, RTrestart, StartTime
    global CursorImage, CursorVisible, InfoScriptPath

    # allocate temporary file
    TempFileName = tempfile.mktemp(prefix="impressive-", suffix="_tmp")

    # some input guesswork
    DocumentTitle = os.path.splitext(os.path.split(FileName)[1])[0]
    if FileName and not(FileList):
        AddFile(FileName)
    if not(FileName) and (len(FileList) == 1):
        FileName = FileList[0]

    # fill the page list
    PageCount = 0
    for name in FileList:
        ispdf = name.lower().endswith(".pdf")
        if ispdf:
            # PDF input -> try to pre-parse the PDF file
            pages = 0
            # phase 1: internal PDF parser
            try:
                pages, pdf_width, pdf_height = analyze_pdf(name)
                if Rotation & 1:
                    pdf_width, pdf_height = (pdf_height, pdf_width)
                res = min(ScreenWidth  * 72.0 / pdf_width, \
                          ScreenHeight * 72.0 / pdf_height)
            except:
                res = 72.0

            # phase 2: use pdftk
            try:
                assert 0 == spawn(os.P_WAIT, pdftkPath, \
                    ["pdftk", FileNameEscape + name + FileNameEscape, \
                     "dump_data", "output", TempFileName + ".txt"])
                title, pages = pdftkParse(TempFileName + ".txt", PageCount)
                if DocumentTitle and title: DocumentTitle = title
            except:
                pass
        else:
            # Image File
            pages = 1
            SetPageProp(PageCount + 1, '_title', os.path.split(name)[-1])

        # validity check
        if not pages:
            print >>sys.stderr, "Warning: The input file `%s' could not be analyzed." % name
            continue

        # add pages and files into PageProps and FileProps
        pagerange = list(range(PageCount + 1, PageCount + pages + 1))
        for page in pagerange:
            SetPageProp(page, '_file', name)
            if ispdf: SetPageProp(page, '_page', page - PageCount)
            title = GetFileProp(name, 'title')
            if title: SetPageProp(page, '_title', title)
        SetFileProp(name, 'pages', GetFileProp(name, 'pages', []) + pagerange)
        SetFileProp(name, 'offsets', GetFileProp(name, 'offsets', []) + [PageCount])
        if not GetFileProp(name, 'stat'): SetFileProp(name, 'stat', my_stat(name))
        if ispdf: SetFileProp(name, 'res', res)
        PageCount += pages

    # no pages? strange ...
    if not PageCount:
        print >>sys.stderr, "The presentation doesn't have any pages, quitting."
        sys.exit(1)

    # if rendering is wanted, do it NOW
    if RenderToDirectory:
        sys.exit(DoRender())

    # load and execute info script
    if not InfoScriptPath:
        InfoScriptPath = FileName + ".info"
    LoadInfoScript()

    # initialize graphics
    pygame.init()
    if Fullscreen and UseAutoScreenSize:
        size = GetScreenSize()
        if size:
            ScreenWidth, ScreenHeight = size
            print >>sys.stderr, "Detected screen size: %dx%d pixels" % (ScreenWidth, ScreenHeight)
    flags = OPENGL|DOUBLEBUF
    if Fullscreen:
        flags |= FULLSCREEN
    try:
        pygame.display.set_mode((ScreenWidth, ScreenHeight), flags)
    except:
        print >>sys.stderr, "FATAL: cannot create rendering surface in the desired resolution (%dx%d)" % (ScreenWidth, ScreenHeight)
        sys.exit(1)
    pygame.display.set_caption(__title__)
    pygame.key.set_repeat(500, 30)
    if Fullscreen:
        pygame.mouse.set_visible(False)
        CursorVisible = False
    glOrtho(0.0, 1.0,  1.0, 0.0,  -10.0, 10.0)
    if (Gamma <> 1.0) or (BlackLevel <> 0):
        SetGamma(force=True)

    # check if graphics are unaccelerated
    renderer = glGetString(GL_RENDERER)
    print >>sys.stderr, "OpenGL renderer:", renderer
    if renderer.lower() in ("mesa glx indirect", "gdi generic"):
        print >>sys.stderr, "WARNING: Using an OpenGL software renderer. Impressive will work, but it will"
        print >>sys.stderr, "         very likely be too slow to be usable."

    # setup the OpenGL texture mode
    Extensions = dict([(ext.split('_', 2)[-1], None) for ext in \
                 glGetString(GL_EXTENSIONS).split()])
    if AllowExtensions and ("texture_non_power_of_two" in Extensions):
        print >>sys.stderr, "Using GL_ARB_texture_non_power_of_two."
        TextureTarget = GL_TEXTURE_2D
        TexWidth  = ScreenWidth
        TexHeight = ScreenHeight
        TexMaxS = 1.0
        TexMaxT = 1.0
    elif AllowExtensions and ("texture_rectangle" in Extensions):
        print >>sys.stderr, "Using GL_ARB_texture_rectangle."
        TextureTarget = 0x84F5  # GL_TEXTURE_RECTANGLE_ARB
        TexWidth  = ScreenWidth
        TexHeight = ScreenHeight
        TexMaxS = ScreenWidth
        TexMaxT = ScreenHeight
    else:
        print >>sys.stderr, "Using conventional power-of-two textures with padding."
        TextureTarget = GL_TEXTURE_2D
        TexWidth  = npot(ScreenWidth)
        TexHeight = npot(ScreenHeight)
        TexMaxS = ScreenWidth  * 1.0 / TexWidth
        TexMaxT = ScreenHeight * 1.0 / TexHeight
    TexSize = TexWidth * TexHeight * 3

    # set up some variables
    if DAR is not None:
        PAR = DAR / float(ScreenWidth) * float(ScreenHeight)
    MeshStepX = 1.0 / MeshResX
    MeshStepY = 1.0 / MeshResY
    PixelX = 1.0 / ScreenWidth
    PixelY = 1.0 / ScreenHeight
    EdgeX = BoxEdgeSize * 1.0 / ScreenWidth
    EdgeY = BoxEdgeSize * 1.0 / ScreenHeight
    if InitialPage is None:
        InitialPage = GetNextPage(0, 1)
    Pcurrent = InitialPage

    # prepare logo image
    LogoImage = Image.open(StringIO.StringIO(LOGO))
    LogoTexture = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, LogoTexture)
    glTexImage2D(GL_TEXTURE_2D, 0, 1, 256, 64, 0, GL_LUMINANCE, GL_UNSIGNED_BYTE, LogoImage.tostring())
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
    DrawLogo()
    pygame.display.flip()

    # initialize OSD font
    try:
        OSDFont = GLFont(FontTextureWidth, FontTextureHeight, FontList, FontSize, search_path=FontPath)
        DrawLogo()
        titles = []
        for key in ('title', '_title'):
            titles.extend([p[key] for p in PageProps.itervalues() if key in p])
        if titles:
            OSDFont.AddString("".join(titles))
    except ValueError:
        print >>sys.stderr, "The OSD font size is too large, the OSD will be rendered incompletely."
    except IOError:
        print >>sys.stderr, "Could not open OSD font file, disabling OSD."
    except (NameError, AttributeError, TypeError):
        print >>sys.stderr, "Your version of PIL is too old or incomplete, disabling OSD."

    # initialize mouse cursor
    if CursorImage:
        try:
            CursorImage = PrepareCustomCursor(Image.open(CursorImage))
        except:
            print >>sys.stderr, "Could not open the mouse cursor image, using standard cursor."
            CursorImage = False

    # set up page cache
    if CacheMode == PersistentCache:
        if not CacheFileName:
            CacheFileName = FileName + ".cache"
        InitPCache()
    if CacheMode == FileCache:
        CacheFile = tempfile.TemporaryFile(prefix="impressive-", suffix=".cache")

    # initialize overview metadata
    OverviewPageMap=[i for i in xrange(1, PageCount + 1) \
        if GetPageProp(i, ('overview', '_overview'), True) \
        and (i >= PageRangeStart) and (i <= PageRangeEnd)]
    OverviewPageCount = max(len(OverviewPageMap), 1)
    OverviewPageMapInv = {}
    for page in xrange(1, PageCount + 1):
        OverviewPageMapInv[page] = len(OverviewPageMap) - 1
        for i in xrange(len(OverviewPageMap)):
            if OverviewPageMap[i] >= page:
                OverviewPageMapInv[page] = i
                break

    # initialize overview page geometry
    OverviewGridSize = 1
    while OverviewPageCount > OverviewGridSize * OverviewGridSize:
        OverviewGridSize += 1
    OverviewCellX = int(ScreenWidth  / OverviewGridSize)
    OverviewCellY = int(ScreenHeight / OverviewGridSize)
    OverviewOfsX = int((ScreenWidth  - OverviewCellX * OverviewGridSize)/2)
    OverviewOfsY = int((ScreenHeight - OverviewCellY * \
                   int((OverviewPageCount + OverviewGridSize - 1) / OverviewGridSize)) / 2)
    OverviewImage = Image.new('RGB', (TexWidth, TexHeight))

    # fill overlay "dummy" images
    dummy = LogoImage.copy()
    border = max(OverviewLogoBorder, 2 * OverviewBorder)
    maxsize = (OverviewCellX - border, OverviewCellY - border)
    if (dummy.size[0] > maxsize[0]) or (dummy.size[1] > maxsize[1]):
        dummy.thumbnail(ZoomToFit(dummy.size, maxsize), Image.ANTIALIAS)
    margX = int((OverviewCellX - dummy.size[0]) / 2)
    margY = int((OverviewCellY - dummy.size[1]) / 2)
    dummy = dummy.convert(mode='RGB')
    for page in range(OverviewPageCount):
        pos = OverviewPos(page)
        OverviewImage.paste(dummy, (pos[0] + margX, pos[1] + margY))
    del dummy

    # set up background rendering
    if not EnableBackgroundRendering:
        print >>sys.stderr, "Background rendering isn't available on this platform."
        BackgroundRendering = False

    # if caching is enabled, pre-render all pages
    if CacheMode and not(BackgroundRendering):
        DrawLogo()
        DrawProgress(0.0)
        pygame.display.flip()
        for pdf in FileProps:
            if pdf.lower().endswith(".pdf"):
                ParsePDF(pdf)
        stop = False
        progress = 0.0
        for page in range(InitialPage, PageCount + 1) + range(1, InitialPage):
            event = pygame.event.poll()
            while event.type != NOEVENT:
                if event.type == KEYDOWN:
                    if (event.key == K_ESCAPE) or (event.unicode == u'q'):
                        Quit()
                    stop = True
                elif event.type == MOUSEBUTTONUP:
                    stop = True
                event = pygame.event.poll()
            if stop: break
            if (page >= PageRangeStart) and (page <= PageRangeEnd):
                PageImage(page)
            DrawLogo()
            progress += 1.0 / PageCount;
            DrawProgress(progress)
            pygame.display.flip()

    # create buffer textures
    DrawLogo()
    pygame.display.flip()
    glEnable(TextureTarget)
    Tcurrent = glGenTextures(1)
    Tnext = glGenTextures(1)
    for T in (Tcurrent, Tnext):
        glBindTexture(TextureTarget, T)
        glTexParameteri(TextureTarget, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(TextureTarget, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(TextureTarget, GL_TEXTURE_WRAP_S, GL_CLAMP)
        glTexParameteri(TextureTarget, GL_TEXTURE_WRAP_T, GL_CLAMP)

    # prebuffer current and next page
    Pnext = 0
    RenderPage(Pcurrent, Tcurrent)
    PageEntered(update_time=False)
    PreloadNextPage(GetNextPage(Pcurrent, 1))

    # some other preparations
    PrepareTransitions()
    GenerateSpotMesh()
    if PollInterval:
        pygame.time.set_timer(USEREVENT_POLL_FILE, PollInterval * 1000)

    # start the background rendering thread
    if CacheMode and BackgroundRendering:
        RTrunning = True
        thread.start_new_thread(RenderThread, (Pcurrent, Pnext))

    # start output and enter main loop
    StartTime = pygame.time.get_ticks()
    pygame.time.set_timer(USEREVENT_TIMER_UPDATE, 100)
    if not(Fullscreen) and CursorImage:
        pygame.mouse.set_visible(False)
    DrawCurrentPage()
    UpdateCaption(Pcurrent)
    while True:
        HandleEvent(pygame.event.wait())


# wrapper around main() that ensures proper uninitialization
def run_main():
    global CacheFile
    try:
        main()
    finally:
        StopMPlayer()
        # ensure that background rendering is halted
        Lrender.acquire()
        Lcache.acquire()
        # remove all temp files
        if 'CacheFile' in globals():
            del CacheFile
        for tmp in glob.glob(TempFileName + "*"):
            try:
                os.remove(tmp)
            except OSError:
                pass
        pygame.quit()


##### COMMAND-LINE PARSER AND HELP #############################################

def if_op(cond, res_then, res_else):
    if cond: return res_then
    else:    return res_else

def HelpExit(code=0):
    print """A nice presentation tool.

Usage: """+os.path.basename(sys.argv[0])+""" [OPTION...] <INPUT(S)...>

You may either play a PDF file, a directory containing image files or
individual image files.

Input options:
  -r,  --rotate <n>       rotate pages clockwise in 90-degree steps
       --scale            scale images to fit screen (not used in PDF mode)
       --supersample      use supersampling (only used in PDF mode)
  -s                      --supersample for PDF files, --scale for image files
  -I,  --script <path>    set the path of the info script
  -u,  --poll <seconds>   check periodically if the source file has been
                          updated and reload it if it did
  -o,  --output <dir>     don't display the presentation, only render to .png
  -h,  --help             show this help text and exit

Output options:
  -f,  --fullscreen       """+if_op(Fullscreen,"do NOT ","")+"""start in fullscreen mode
  -g,  --geometry <WxH>   set window size or fullscreen resolution
  -A,  --aspect <X:Y>     adjust for a specific display aspect ratio (e.g. 5:4)
  -G,  --gamma <G[:BL]>   specify startup gamma and black level

Page options:
  -i,  --initialpage <n>  start with page <n>
  -p,  --pages <A-B>      only cache pages in the specified range;
                          implicitly sets -i <A>
  -w,  --wrap             go back to the first page after the last page
  -a,  --auto <seconds>   automatically advance to next page after some seconds
  -O,  --autooverview <x> automatically derive page visibility on overview page
                            -O first = show pages with captions
                            -O last  = show pages before pages with captions

Display options:
  -t,  --transition <trans[,trans2...]>
                          force a specific transitions or set of transitions
  -l,  --listtrans        print a list of available transitions and exit
  -F,  --font <file>      use a specific TrueType font file for the OSD
  -S,  --fontsize <px>    specify the OSD font size in pixels
  -C,  --cursor <F[:X,Y]> use a .png image as the mouse cursor
  -L,  --layout <spec>    set the OSD layout (please read the documentation)

Timing options:
  -M,  --minutes          display time in minutes, not seconds
  -d,  --duration <time>  set the desired duration of the presentation and show
                          a progress bar at the bottom of the screen
  -T,  --transtime <ms>   set transition duration in milliseconds
  -D,  --mousedelay <ms>  set mouse hide delay for fullscreen mode (in ms)
  -B,  --boxfade <ms>     set highlight box fade duration in milliseconds
  -Z,  --zoom <ms>        set zoom duration in milliseconds

Advanced options:
  -c,  --cache <mode>     set page cache mode:
                            -c none       = disable caching completely
                            -c memory     = store cache in RAM
                            -c disk       = store cache on disk temporarily
                            -c persistent = store cache on disk persistently
       --cachefile <path> set the persistent cache file path (implies -cp)
  -b,  --noback           don't pre-render images in the background
  -P,  --gspath <path>    set path to GhostScript or pdftoppm executable
  -R,  --meshres <XxY>    set mesh resolution for effects (default: 48x36)
  -e,  --noext            don't use OpenGL texture size extensions

For detailed information, visit""", __website__
    sys.exit(code)

def ListTransitions():
    print "Available transitions:"
    standard = dict([(tc.__name__, None) for tc in AvailableTransitions])
    trans = [(tc.__name__, tc.__doc__) for tc in AllTransitions]
    trans.append(('None', "no transition"))
    trans.sort()
    maxlen = max([len(item[0]) for item in trans])
    for name, desc in trans:
        if name in standard:
            star = '*'
        else:
            star = ' '
        print star, name.ljust(maxlen), '-', desc
    print "(transitions with * are enabled by default)"
    sys.exit(0)

def TryTime(s, regexp, func):
    m = re.match(regexp, s, re.I)
    if not m: return 0
    return func(map(int, m.groups()))
def ParseTime(s):
    return TryTime(s, r'([0-9]+)s?$', lambda m: m[0]) \
        or TryTime(s, r'([0-9]+)m$', lambda m: m[0] * 60) \
        or TryTime(s, r'([0-9]+)[m:]([0-9]+)[ms]?$', lambda m: m[0] * 60 + m[1]) \
        or TryTime(s, r'([0-9]+)[h:]([0-9]+)[hm]?$', lambda m: m[0] * 3600 + m[1] * 60) \
        or TryTime(s, r'([0-9]+)[h:]([0-9]+)[m:]([0-9]+)s?$', lambda m: m[0] * 3600 + m[1] * 60 + m[2])

def opterr(msg):
    print >>sys.stderr, "command line parse error:", msg
    print >>sys.stderr, "use `%s -h' to get help" % sys.argv[0]
    print >>sys.stderr, "or visit", __website__, "for full documentation"
    sys.exit(2)

def SetTransitions(list):
    global AvailableTransitions
    index = dict([(tc.__name__.lower(), tc) for tc in AllTransitions])
    index['none'] = None
    AvailableTransitions=[]
    for trans in list.split(','):
        try:
            AvailableTransitions.append(index[trans.lower()])
        except KeyError:
            opterr("unknown transition `%s'" % trans)

def ParseLayoutPosition(value):
    xpos = []
    ypos = []
    for c in value.strip().lower():
        if   c == 't': ypos.append(0)
        elif c == 'b': ypos.append(1)
        elif c == 'l': xpos.append(0)
        elif c == 'r': xpos.append(1)
        elif c == 'c': xpos.append(2)
        else: opterr("invalid position specification `%s'" % value)
    if not xpos: opterr("position `%s' lacks X component" % value)
    if not ypos: opterr("position `%s' lacks Y component" % value)
    if len(xpos)>1: opterr("position `%s' has multiple X components" % value)
    if len(ypos)>1: opterr("position `%s' has multiple Y components" % value)
    return (xpos[0] << 1) | ypos[0]
def SetLayoutSubSpec(key, value):
    global OSDTimePos, OSDTitlePos, OSDPagePos, OSDStatusPos
    global OSDAlpha, OSDMargin
    lkey = key.strip().lower()
    if lkey in ('a', 'alpha', 'opacity'):
        try:
            OSDAlpha = float(value)
        except ValueError:
            opterr("invalid alpha value `%s'" % value)
        if OSDAlpha > 1.0:
            OSDAlpha *= 0.01  # accept percentages, too
        if (OSDAlpha < 0.0) or (OSDAlpha > 1.0):
            opterr("alpha value %s out of range" % value)
    elif lkey in ('margin', 'dist', 'distance'):
        try:
            OSDMargin = float(value)
        except ValueError:
            opterr("invalid margin value `%s'" % value)
        if OSDMargin < 0:
            opterr("margin value %s out of range" % value)
    elif lkey in ('t', 'time'):
        OSDTimePos = ParseLayoutPosition(value)
    elif lkey in ('title', 'caption'):
        OSDTitlePos = ParseLayoutPosition(value)
    elif lkey in ('page', 'number'):
        OSDPagePos = ParseLayoutPosition(value)
    elif lkey in ('status', 'info'):
        OSDStatusPos = ParseLayoutPosition(value)
    else:
        opterr("unknown layout element `%s'" % key)
def SetLayout(spec):
    for sub in spec.replace(':', '=').split(','):
        try:
            key, value = sub.split('=')
        except ValueError:
            opterr("invalid layout spec `%s'" % sub)
        SetLayoutSubSpec(key, value)

def ParseCacheMode(arg):
    arg = arg.strip().lower()
    if "none".startswith(arg): return NoCache
    if "off".startswith(arg): return NoCache
    if "memory".startswith(arg): return MemCache
    if "disk".startswith(arg): return FileCache
    if "file".startswith(arg): return FileCache
    if "persistent".startswith(arg): return PersistentCache
    opterr("invalid cache mode `%s'" % arg)

def ParseAutoOverview(arg):
    arg = arg.strip().lower()
    if "off".startswith(arg): return Off
    if "first".startswith(arg): return First
    if "last".startswith(arg): return Last
    try:
        i = int(arg)
        assert (i >= Off) and (i <= Last)
    except:
        opterr("invalid auto-overview mode `%s'" % arg)

def ParseOptions(argv):
    global FileName, FileList, Fullscreen, Scaling, Supersample, CacheMode
    global TransitionDuration, MouseHideDelay, BoxFadeDuration, ZoomDuration
    global ScreenWidth, ScreenHeight, MeshResX, MeshResY, InitialPage, Wrap
    global AutoAdvance, RenderToDirectory, Rotation, AllowExtensions, DAR
    global BackgroundRendering, UseAutoScreenSize, PollInterval, CacheFileName
    global PageRangeStart, PageRangeEnd, FontList, FontSize, Gamma, BlackLevel
    global EstimatedDuration, CursorImage, CursorHotspot, MinutesOnly
    global GhostScriptPath, pdftoppmPath, UseGhostScript, InfoScriptPath
    global AutoOverview

    try:  # unused short options: jknqvxyzEHJKNQUVWXY
        opts, args = getopt.getopt(argv, \
            "hfg:sc:i:wa:t:lo:r:T:D:B:Z:P:R:eA:mbp:u:F:S:G:d:C:ML:I:O:", \
           ["help", "fullscreen", "geometry=", "scale", "supersample", \
            "nocache", "initialpage=", "wrap", "auto", "listtrans", "output=", \
            "rotate=", "transition=", "transtime=", "mousedelay=", "boxfade=", \
            "zoom=", "gspath=", "meshres=", "noext", "aspect", "memcache", \
            "noback", "pages=", "poll=", "font=", "fontsize=", "gamma=",
            "duration=", "cursor=", "minutes", "layout=", "script=", "cache=",
            "cachefile=", "autooverview="])
    except getopt.GetoptError, message:
        opterr(message)

    for opt, arg in opts:
        if opt in ("-h", "--help"):
            HelpExit()
        if opt in ("-l", "--listtrans"):
            ListTransitions()
        if opt in ("-f", "--fullscreen"):
            Fullscreen = not(Fullscreen)
        if opt in ("-e", "--noext"):
            AllowExtensions = not(AllowExtensions)
        if opt in ("-s", "--scale"):
            Scaling = not(Scaling)
        if opt in ("-s", "--supersample"):
            Supersample = 2
        if opt in ("-w", "--wrap"):
            Wrap = not(Wrap)
        if opt in ("-O", "--autooverview"):
            AutoOverview = ParseAutoOverview(arg)
        if opt in ("-c", "--cache"):
            CacheMode = ParseCacheMode(arg)
        if opt == "--nocache":
            print >>sys.stderr, "Note: The `--nocache' option is deprecated, use `--cache none' instead."
            CacheMode = NoCache
        if opt in ("-m", "--memcache"):
            print >>sys.stderr, "Note: The `--memcache' option is deprecated, use `--cache memory' instead."
            CacheMode = MemCache
        if opt == "--cachefile":
            CacheFileName = arg
            CacheMode = PersistentCache
        if opt in ("-M", "--minutes"):
            MinutesOnly = not(MinutesOnly)
        if opt in ("-b", "--noback"):
            BackgroundRendering = not(BackgroundRendering)
        if opt in ("-t", "--transition"):
            SetTransitions(arg)
        if opt in ("-L", "--layout"):
            SetLayout(arg)
        if opt in ("-o", "--output"):
            RenderToDirectory = arg
        if opt in ("-I", "--script"):
            InfoScriptPath = arg
        if opt in ("-F", "--font"):
            FontList = [arg]
        if opt in ("-P", "--gspath"):
            UseGhostScript = (arg.replace("\\", "/").split("/")[-1].lower().find("pdftoppm") < 0)
            if UseGhostScript:
                GhostScriptPath = arg
            else:
                pdftoppmPath = arg
        if opt in ("-S", "--fontsize"):
            try:
                FontSize = int(arg)
                assert FontSize > 0
            except:
                opterr("invalid parameter for --fontsize")
        if opt in ("-i", "--initialpage"):
            try:
                InitialPage = int(arg)
                assert InitialPage > 0
            except:
                opterr("invalid parameter for --initialpage")
        if opt in ("-d", "--duration"):
            try:
                EstimatedDuration = ParseTime(arg)
                assert EstimatedDuration > 0
            except:
                opterr("invalid parameter for --duration")
        if opt in ("-a", "--auto"):
            try:
                AutoAdvance = int(arg) * 1000
                assert (AutoAdvance > 0) and (AutoAdvance <= 86400000)
            except:
                opterr("invalid parameter for --auto")
        if opt in ("-T", "--transtime"):
            try:
                TransitionDuration = int(arg)
                assert (TransitionDuration >= 0) and (TransitionDuration < 32768)
            except:
                opterr("invalid parameter for --transtime")
        if opt in ("-D", "--mousedelay"):
            try:
                MouseHideDelay = int(arg)
                assert (MouseHideDelay >= 0) and (MouseHideDelay < 32768)
            except:
                opterr("invalid parameter for --mousedelay")
        if opt in ("-B", "--boxfade"):
            try:
                BoxFadeDuration = int(arg)
                assert (BoxFadeDuration >= 0) and (BoxFadeDuration < 32768)
            except:
                opterr("invalid parameter for --boxfade")
        if opt in ("-Z", "--zoom"):
            try:
                ZoomDuration = int(arg)
                assert (ZoomDuration >= 0) and (ZoomDuration < 32768)
            except:
                opterr("invalid parameter for --zoom")
        if opt in ("-r", "--rotate"):
            try:
                Rotation = int(arg)
            except:
                opterr("invalid parameter for --rotate")
            while Rotation < 0: Rotation += 4
            Rotation = Rotation & 3
        if opt in ("-u", "--poll"):
            try:
                PollInterval = int(arg)
                assert PollInterval >= 0
            except:
                opterr("invalid parameter for --poll")
        if opt in ("-g", "--geometry"):
            try:
                ScreenWidth, ScreenHeight = map(int, arg.split("x"))
                assert (ScreenWidth  >= 320) and (ScreenWidth  < 4096)
                assert (ScreenHeight >= 200) and (ScreenHeight < 4096)
                UseAutoScreenSize = False
            except:
                opterr("invalid parameter for --geometry")
        if opt in ("-R", "--meshres"):
            try:
                MeshResX, MeshResY = map(int, arg.split("x"))
                assert (MeshResX > 0) and (MeshResX <= ScreenWidth)
                assert (MeshResY > 0) and (MeshResY <= ScreenHeight)
            except:
                opterr("invalid parameter for --meshres")
        if opt in ("-p", "--pages"):
            try:
                PageRangeStart, PageRangeEnd = map(int, arg.split("-"))
                assert PageRangeStart > 0
                assert PageRangeStart <= PageRangeEnd
            except:
                opterr("invalid parameter for --pages")
            InitialPage=PageRangeStart
        if opt in ("-A", "--aspect"):
            try:
                if ':' in arg:
                    fx, fy = map(float, arg.split(':'))
                    DAR = fx / fy
                else:
                    DAR = float(arg)
                assert DAR > 0.0
            except:
                opterr("invalid parameter for --aspect")
        if opt in ("-G", "--gamma"):
            try:
                if ':' in arg:
                    arg, bl = arg.split(':', 1)
                    BlackLevel = int(bl)
                Gamma = float(arg)
                assert Gamma > 0.0
                assert (BlackLevel >= 0) and (BlackLevel < 255)
            except:
                opterr("invalid parameter for --gamma")
        if opt in ("-C", "--cursor"):
            try:
                if ':' in arg:
                    arg = arg.split(':')
                    assert len(arg) > 1
                    CursorImage = ':'.join(arg[:-1])
                    CursorHotspot = map(int, arg[-1].split(','))
                else:
                    CursorImage = arg
                assert (BlackLevel >= 0) and (BlackLevel < 255)
            except:
                opterr("invalid parameter for --cursor")

    for arg in args:
        AddFile(arg)
    if not FileList:
        opterr("no playable files specified")
    return

    # glob and filter argument list
    files = []
    for arg in args:
        files.extend(glob.glob(arg))
    files = list(filter(IsPlayable, files))

    # if only one argument is specified, use it as the informal file name
    if len(files) == 1:
        FileName = files[0]
    else:
        FileName = ""

    # construct final FileList by expanding directories to image file lists
    FileList = []
    for item in files:
        if os.path.isdir(item):
            images = [os.path.join(item, f) for f in os.listdir(item) if IsImageFileName(f)]
            images.sort(lambda a, b: cmp(a.lower(), b.lower()))
            FileList.extend(images)
        else:
            FileList.append(item)

    if not FileList:
        opterr("no playable files specified")


# use this function if you intend to use Impressive as a library
def run():
    try:
        run_main()
    except SystemExit, e:
        return e.code

if __name__=="__main__":
    ParseOptions(sys.argv[1:])
    run_main()
