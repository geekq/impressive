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

_impressive_ is written in python and the source code seems to be 
a perfect foundation:

* the code looks clean
* it is a bit C style, not object oriented - a lot of global, 
  not (deeper) structured variables, but it is OK


Restructure
-----------
While I am going to procede as conservative as possible to enable the
integration of my extension upstream, following (bigger) improvements
came into my mind:

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

