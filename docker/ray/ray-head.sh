#!/bin/sh
set -e
exec ray start --head --block --dashboard-host=0.0.0.0 --dashboard-port=8265 --disable-usage-stats
