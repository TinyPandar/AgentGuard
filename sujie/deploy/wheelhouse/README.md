# Offline wheelhouse

此目录默认不提交 wheel。正常联网构建从锁文件安装；VM 无外网时，将与
`requirements.lock` 对应的 Linux/CPython 3.12 wheels 放入此目录，并设置：

```sh
export SUJIE_OFFLINE_BUILD=1
export SUJIE_PYTHON_BASE=sujie/python-base:3.12.13
```

离线 wheel 必须按精确锁定版本下载，并在 VM 内由 `pip --no-index` 校验依赖完整性。
