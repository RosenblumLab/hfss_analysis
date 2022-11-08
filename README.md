# HFSS&pyEPR-examples

This repository contains some exaples of HFSS designs and how to simulate them using `pyEPR`.

## Quantum analysis
This wrapper was written by Uri and faciliates the use of pyEPR by a lot. Use it and check out the [example](QuantumAnalysis/example.py) there.

## Examples

Analyses can be static, where parameters of a single design are calculated, or sweep, where a python loop goes over a parameter (or more) and plots the different results. The latter is useful when choosing design parameters.

The `losses` folder (and module) calculates predicated quality factors due to different loss channels. It is purely classical and does not involve any quantum effects, pyEPR is only used there for communication with HFSS.

## Common Errors
Some common errors and (hopefully) ways to go around them. Please add to this file whenever you encounter something.

## Credits
Daniel has done a lot writing the notebooks and building the first HFSS simulations of the lab. Go check his [page](https://github.com/DanielCohenHillel).
