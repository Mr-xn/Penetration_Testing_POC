#ifndef definitions_h
#define definitions_h

#include <string.h>    // memset
#include <mach/mach.h> // thread_set_state

#pragma pack(4)

#define x86_SAVED_STATE32        THREAD_STATE_NONE + 1
#define x86_SAVED_STATE64        THREAD_STATE_NONE + 2

struct x86_saved_state32 {
    uint32_t    gs;     // 0x00
    uint32_t    fs;
    uint32_t    es;     // 0x08
    uint32_t    ds;
    uint32_t    edi;    // 0x10
    uint32_t    esi;
    uint32_t    ebp;    // 0x18
    uint32_t    cr2;
    uint32_t    ebx;    // 0x20
    uint32_t    edx;
    uint32_t    ecx;    // 0x28
    uint32_t    eax;
    uint16_t    trapno; // 0x30
    uint16_t    cpu;    // 0x32
    uint32_t    err;    // 0x34
    uint32_t    eip;
    uint32_t    cs;     // 0x3c
    uint32_t    efl;
    uint32_t    uesp;   // 0x44
    uint32_t    ss;
};
typedef struct x86_saved_state32 x86_saved_state32_t;

#define x86_SAVED_STATE32_COUNT    ((mach_msg_type_number_t) \
(sizeof (x86_saved_state32_t)/sizeof(unsigned int)))

#pragma pack(0)

#endif /* definitions_h */
