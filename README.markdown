Motivation for the _impress!ve_ fork
====================================

[impressive][] is the best software available on linux for showing
PDF based presentations.

Macs have the perfect presentation software: while an external beamer
shows the slide you are talking about, your notebook shows

* the current slide
* the next slide
* time elapsed for the current slide
* total elapsed time

This is **exactly** what I need and what _impressive_ is unfortunately
missing - the dual monitor feature.

_impressive_ is written in python and uses OpenGL for rendering, so 
I thought, I'll add the desired feature.


Dual-Head support
-----------------

My fork provides a new command line option `dual-head`.
On my notebook I typically run the presentation tool with

    /path/to/impressive.py -t None \
      --dual-head 1024x768+1280+31,1280x800+0+0 \
      pres.pdf' 

because 

* my notebook has a screen resolution of 1280x800
* typical projector has a resolution of 1024x768
* I use xrandr and big screen, where the display area of the external output 
  is to the right of the notebook display, this leads to horizontal offset 
  of +1280
* OpenGL coordinates use bottom left corner, so we normally would need a
  vertical offset of +32 (=800-768)
* but I had to adjust it by one pixel to remove an unsightly border at the 
  bottom of the slide - some rounding problems or OpenGL anomaly
* so the leads to the offset of +1280+31 for the external output (projector)


Please note: the new feature is not compatible with all the other options
of impressive, that deal with resolution, picture size and screen size
detection. Transitions also do not work. This because the implementation of
impressive is so complicated, that it is not possible to introduce an 
implementation for a new cross cutting concern without breaking everything.


Restructure
-----------
I hope, someday I have enough time to refactor the original implementation
and implement following ideas:

* a single file is an advantage, but a file of 4000 lines length is probably not
* swap optional stuff like implementation of transitions out, so they
  can be included with `import` if needed
* make the whole thing more modular and organize it as a set of functions,
  that can be tied together with a small wrapper script; everybody could
  write its own integration script using units like 
  * parse PDF
  * render one slide to a rectengular area
  * show text on OSD
  * caching
  * overview mode

About
-----
More about presentations for geeks can be found on my blog
<http://blog.geekq.net/2009/03/29/impressive-presentation-for-geeks/>.

[keyJ]: http://keyj.s2000.ws/
[impressive]: http://impressive.sourceforge.net/

