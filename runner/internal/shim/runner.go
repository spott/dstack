package shim

import (
	"context"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"strconv"
	"strings"
	"time"

	"github.com/dstackai/dstack/runner/internal/gerrors"
)

const (
	DstackRunnerURL        = "https://%s.s3.eu-west-1.amazonaws.com/%s/binaries/dstack-runner-%s-%s"
	DstackReleaseBucket    = "dstack-runner-downloads"
	DstackStagingBucket    = "dstack-runner-downloads-stgn"
	DstackRunnerBinaryName = "/usr/local/bin/dstack-runner"
)

func (c *CLIArgs) GetDockerCommands() []string {
	return []string{
		// start runner
		fmt.Sprintf("%s %s", DstackRunnerBinaryName, strings.Join(c.getRunnerArgs(), " ")),
	}
}

func (c *CLIArgs) DownloadRunner() error {
	url := makeDownloadRunnerUrl(c.Runner.Version, c.Runner.DevChannel)

	runnerBinaryPath, err := downloadRunner(url)
	if err != nil {
		return gerrors.Wrap(err)
	}

	c.Runner.BinaryPath = runnerBinaryPath

	return nil
}

func (c *CLIArgs) getRunnerArgs() []string {
	return []string{
		"--log-level", strconv.Itoa(c.Runner.LogLevel),
		"start",
		"--http-port", strconv.Itoa(c.Runner.HTTPPort),
		"--temp-dir", c.Runner.TempDir,
		"--home-dir", c.Runner.HomeDir,
		"--working-dir", c.Runner.WorkingDir,
	}
}

func makeDownloadRunnerUrl(version string, staging bool) string {
	bucket := DstackReleaseBucket
	if staging {
		bucket = DstackStagingBucket
	}

	osName := "linux"
	archName := "amd64"

	url := fmt.Sprintf(DstackRunnerURL, bucket, version, osName, archName)
	return url
}

func downloadRunner(url string) (string, error) {
	tempFile, err := os.CreateTemp("", "dstack-runner")
	if err != nil {
		return "", gerrors.Wrap(err)
	}
	defer func() {
		err := tempFile.Close()
		if err != nil {
			log.Printf("close file error: %s\n", err)
		}
	}()

	log.Printf("Downloading runner from %s\n", url)
	ctx, cancel := context.WithTimeout(context.Background(), time.Second*600)
	defer cancel()

	req, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
	if err != nil {
		return "", gerrors.Wrap(err)
	}

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return "", gerrors.Wrap(err)
	}
	defer func() {
		err := resp.Body.Close()
		log.Printf("close body error: %s\n", err)
	}()

	if resp.StatusCode != http.StatusOK {
		return "", gerrors.Newf("unexpected status code: %s", resp.Status)
	}

	_, err = io.Copy(tempFile, resp.Body)
	if err != nil {
		return "", gerrors.Wrap(err)
	}

	if err := tempFile.Chmod(0755); err != nil {
		return "", gerrors.Wrap(err)
	}

	return tempFile.Name(), nil
}
