#
# Makefile
#
# Created by Ilias Morad.
# Copyright © 2019 Ilias Morad. All rights reserved.
#

main: exploit.c gadgets.c kernel.s
	nasm -f macho32 -o kernel.o kernel.s
	gcc -o exploit -m32 -Wl,-pagezero_size,0 -masm=intel exploit.c gadgets.c kernel.o

clean:
	rm exploit *.o