package main

import (
	"net/http"
	"strings"
)

type DetectMethod struct {
	PHPOptionEnable  string
	PHPOptionDisable string
	Check            func(resp *http.Response, data []byte) bool
}

var Methods = map[string]*DetectMethod{
	"session.auto_start": {
		PHPOptionEnable:  "session.auto_start=1",
		PHPOptionDisable: "session.auto_start=0",
		Check: func(resp *http.Response, _ []byte) bool {
			return strings.Contains(resp.Header.Get("set-cookie"), "PHPSESSID")
		},
	},
	"output_handler.md5": {
		PHPOptionEnable:  "output_handler=md5",
		PHPOptionDisable: "output_handler=NULL",
		Check: func(_ *http.Response, data []byte) bool {
			return len(data) == 16
		},
	},
}
