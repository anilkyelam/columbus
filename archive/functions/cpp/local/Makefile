CC=g++
CFLAGS=-I.
DEPS = 
OBJ = 

%.o: %.c $(DEPS)
	$(CC) -c -o $@ $< $(CFLAGS)

all: thrasher sampler

thrasher: local.cpp
	$(CC) -o $@ $^ $(CFLAGS) -DTHRASHER
	
sampler: local.cpp
	$(CC) -o $@ $^ $(CFLAGS) -DSAMPLER

.PHONY: clean

clean:
	rm -r thrasher sampler
