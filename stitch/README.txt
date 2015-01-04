See pr0nauto script for example workflow

you *might* need a file like this to get it working:
$ cat ~/.pr0nrc
{
	"keep_temp":1,
	"pr0nts": {
		"mem":"6144m"
	},
	"enblend": {
		"opts":"-m 6144"
	}
}

above file is for 6GB of RAM
