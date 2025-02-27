#!/bin/bash
gunicorn -w 4 -b 0.0.0.0:9099 app:app
