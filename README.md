# HFSS&pyEPR-examples

This repository contains some exaples of HFSS designs and how to simulate them using `pyEPR`.

Analyses can be static, where parameters of a single design are calculated, or sweep, where a python loop goes over a parameter (or more) and plots the different results. The latter is useful when choosing design parameters.

The losses folder (and module) calculates predicated quality factors due to different loss channels. It is purely classical and does not involve any quantum effects, pyEPR is only used there for communication with HFSS.

Daniel has done a lot writing the notebooks and building the first HFSS simulations of the lab. Go check his [page](https://github.com/DanielCohenHillel).
