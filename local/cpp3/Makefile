CC=g++
CFLAGS=-I.
DEPS = 
OBJ = 

%.o: %.c $(DEPS)
	$(CC) -c -o $@ $< $(CFLAGS)

all: lambda

lambda: lambda.cpp kstest.cpp util.cpp timsort.cpp
	$(CC) -o $@ $^ $(CFLAGS) 
	

.PHONY: clean

clean:
	rm -r lambda
