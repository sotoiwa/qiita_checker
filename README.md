# qiita_checker

## Usage

Build and push image.

```shell
docker build -t sotoiwa540/qiita-checker:latest .
docker push sotoiwa540/qiita-checker:latest
```

Create alias.

```shell
alias qiitacheck='docker run --rm -it -e QIITA_TOKEN=${QIITA_TOKEN} -v ${PWD}:/tmp sotoiwa540/qiita-checker:1.1'
```

Export token.

```shell
export QIITA_TOKEN=hogehoge
```

Execute command.

```shell
qiitacheck --help
```