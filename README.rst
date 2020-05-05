.. image:: icons/radiopadre-logo-long-400px.png?raw=True 
   :width: 400

Python (Radio) Astronomy Data & Results Examiner
================================================

|Build Status|
|PyPI version|
|PyPI pyversions|
|PyPI status|
|Project License|

Radiopadre is a Jupyter
notebook framework for quick and easy visualization of [radio astronomy, primarily]
data products and pipelines.

**Radiopadre includes integration with** `JS9 <https://js9.si.edu/>`_
**and** `CARTA <https://cartavis.github.io/>`_
**for live FITS viewing of [remote] FITS files straight from your browser.**
(In boldface, because this is a pretty neat capability to have!)

Radiopadre is a custom Jupyter kernel, so in principle you could install it
and create radiopadre notebooks directly from a Jupyter session. Some of the
tight integration with JS9 and CARTA, however, works smoother if you start your sessions
via the ``run-radiopadre`` `client script <https://github.com/ratt-ru/radiopadre-client>`_,
which takes care of starting up and stopping appropriate
helper processes and such.

The general use case for Radiopadre is "here I am sitting with a slow ssh connection into a remote cluster node, my pipeline has produced 500 plots/logs/FITS images, how do I make sense of this mess?" More specifically, there are three (somewhat overlapping) scenarios that Radiopadre is designed for:

* Just browsing: interactively exploring the aforementioned 500 files using a notebook.

* Automated reporting: customized Radiopadre notebooks that automatically generate a report composed of a pipeline's outputs and intermediate products. Since your pipeline's output is (hopefully!) structured, i.e. in terms of filename conventions etc., you can write a notebook to exploit that structure and make a corresponding report automatically.

* Sharing notebooks: fiddle with a notebook until everything is visualized just right, insert explanatory text in mardkdown cells in between, voila, you have an instant report you can share with colleagues.

======================
Usage, in a nutshell
======================

See `radiopadre-client package <https://github.com/ratt-ru/radiopadre-client>`_.


==========
Tutorial
==========

For a quick tutorial on radiopadre, download the tutorial_package_,
untar, and run radiopadre inside the resulting directory, locally or remotely (you can also refer to the PDF 
enclosed in the tarball for a poor man's rendering of the notebook).

.. |Build Status| image:: https://travis-ci.org/ratt-ru/radiopadre.svg?branch=master
                  :target: https://travis-ci.org/radio-astro/radiopadre/
                  :alt:

.. |PyPI version| image:: https://img.shields.io/pypi/v/radiopadre.svg
                  :target: https://pypi.python.org/pypi/radiopadre/
                  :alt:

.. |PyPI pyversions| image:: https://img.shields.io/pypi/pyversions/radiopadre.svg
                  :target: https://pypi.python.org/pypi/radiopadre/
                  :alt:

.. |PyPI status| image:: https://img.shields.io/pypi/status/radiopadre.svg
                  :target: https://pypi.python.org/pypi/radiopadre/
                  :alt:
.. |Project License| image:: https://img.shields.io/github/license/ratt-ru/radiopadre
                     :target: https://github.com/ratt-ru/radiopadre/blob/master/LICENSE
                     :alt:

.. _tutorial_package: https://www.dropbox.com/sh/be4pc23rsavj67s/AAB2Ejv8cLsVT8wj60DiqS8Ya?dl=0
