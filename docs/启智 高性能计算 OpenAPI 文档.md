# 启智 高性能计算 OpenAPI 文档

## 1. API 概述

本文介绍启智 API 的描述、语法、参数说明及示例。你可以通过调用 API 的方式来管理启智服务。

启智 API 当前处于 Alpha 版本阶段，后续更新可能无法保证前向兼容性。如有生产级应用需求，请预先联系启智团队。

## 2. 基本概念

| 名称 | 说明 |
| --- | --- |
| 账号 | 账号是在启智平台的身份凭证，是启智资源归属和计量计费的主体。使用启智服务前，需要先注册生成账号。该账号用于启智控制台登录和 API 调用。 |
| Token | 数字身份标识，包含用户身份信息。调用 API 前，需要先通过账号（用户名和密码）获取 Bearer Token，并在后续请求头中携带。 |

请求头示例：

```http
Authorization: Bearer <token>
```

## 3. API 列表

| API 名称 | 功能 |
| --- | --- |
| Create | 创建高性能计算任务。 |
| Detail | 获取高性能计算任务详情。 |
| Stop | 停止高性能计算任务。 |

## 4. 调用方式

### 4.1 服务地址

`qz.sii.edu.cn`

### 4.2 鉴权机制

1. 获取访问 Token。
2. 在访问 OpenAPI 时，将 Access Token 放入 HTTP 请求头。

示例：

```bash
curl --location 'http://qz.sii.edu.cn/openapi/v1/hpc_jobs/create' \
  --header 'Authorization: Bearer xxx'
```

### 4.3 错误码

| 错误代码 Code | HTTP 状态码 | 错误信息 Message | 处理措施 |
| --- | --- | --- | --- |
| 429 | 429 | Too Many Requests | 接口触发频控，请降低调用频次。 |
| -100000 | 400 | 参数校验错误 | 检查请求参数是否满足业务接口要求。 |
| 500 | 500 | 内部服务错误 | 联系启智 Oncall。 |

## 5. Token 管理

### 5.1 获取当前身份的 Access Token

#### 请求说明

- 请求方式：`POST`。
- 请求地址：`https://qz.sii.edu.cn/auth/token`。

#### 请求参数

| 参数 | 类型 | 是否必选 | 示例值 | 描述 |
| --- | --- | --- | --- | --- |
| username | String | 是 | xxx | 用户名。 |
| password | String | 是 | xxx | 密码。 |

#### 请求示例

```bash
curl --location --request POST 'https://qz.sii.edu.cn/auth/token' \
  --data-raw '{
    "password": "xxxxxxxx",
    "username": "xxxxxxxx"
  }'
```

#### 返回参数

| 参数 | 类型 | 示例值 | 描述 |
| --- | --- | --- | --- |
| code | Integer | 0 | 错误代码。0 表示成功，非 0 表示发生错误。 |
| message | String | 错误信息 | 错误信息。 |
| data | Object | 见下方示例 | Token 信息，包括 access_token、expires_in、token_type 等。 |

`data` 示例：

```json
{
  "access_token": "eyJhxxx",
  "expires_in": "604800",
  "token_type": "Bearer"
}
```

## 6. 高性能计算

### 6.1 创建高性能计算任务

#### 请求说明

- 请求方式：`POST`。
- 请求地址：`https://qz.sii.edu.cn/openapi/v1/hpc_jobs/create`。

#### 请求参数

| 参数 | 类型 | 是否必选 | 示例值 | 描述 |
| --- | --- | --- | --- | --- |
| name | String | 是 | test_openapi | 高性能计算任务名称。 |
| logic_compute_group_id | String | 是 | lcg-xxxx | 计算资源组 ID。 |
| project_id | String | 是 | project-xxxx | 项目 ID。 |
| image | String | 是 | docker.sii.shaipower.online/inspire-studio/slurm-gromacs:xxx | 镜像名称。 |
| image_type | String | 是 | SOURCE_PUBLIC | 镜像类型，可选 SOURCE_PUBLIC、SOURCE_PRIVATE、SOURCE_OFFICIAL。 |
| entrypoint | String | 是 | sleep 1 | 启动命令。 |
| instance_count | Integer | 是 | 1 | 实例数目。 |
| task_priority | Integer | 是 | 4 | 任务优先级。 |
| workspace_id | String | 是 | ws-xxxx | 工作空间 ID。 |
| spec_id | String | 是 | xxxx | 规格 ID。可在平台创建 demo 任务后通过 detail 接口返回的 quota_id 获取。 |
| ttl_after_finish_seconds | Integer | 否 | 600 | 任务结束后保留时长（秒）。 |
| number_of_tasks | Integer | 是 | 2 | 子任务数量。 |
| cpus_per_task | Integer | 是 | 1 | 单个任务 CPU 核数。 |
| memory_per_cpu | String | 是 | 4G | 每个 CPU 的内存配置。 |
| enable_hyper_threading | Boolean | 是 | false | 是否开启超线程。 |

#### 请求示例

```bash
curl --location --request POST 'https://qz.sii.edu.cn/openapi/v1/hpc_jobs/create' \
  --header 'Authorization: Bearer xxxx' \
  --data-raw '{
    "name": "test_openapi",
    "logic_compute_group_id": "lcg-xxxx",
    "project_id": "project-xxxx",
    "entrypoint": "sleep 1",
    "image": "docker.sii.shaipower.online/inspire-studio/slurm-gromacs:xxx",
    "image_type": "SOURCE_PUBLIC",
    "instance_count": 1,
    "spec_id": "xxxx",
    "workspace_id": "ws-xxxx",
    "number_of_tasks": 1,
    "cpus_per_task": 1,
    "memory_per_cpu": "4G",
    "enable_hyper_threading": false
  }'
```

#### 返回参数

| 参数 | 类型 | 示例值 | 描述 |
| --- | --- | --- | --- |
| code | Integer | 0 | 错误代码。0 表示成功，非 0 表示发生错误。 |
| message | String | 错误信息 | 错误信息。 |
| data | Object | 任务信息 | 任务创建结果。 |

### 6.2 查询高性能计算任务

#### 请求说明

- 请求方式：`POST`。
- 请求地址：`https://qz.sii.edu.cn/openapi/v1/hpc_jobs/detail`。

#### 请求参数

| 参数 | 类型 | 是否必选 | 示例值 | 描述 |
| --- | --- | --- | --- | --- |
| job_id | String | 是 | hpc-job-7768776e-16b5-4b09-a61e-e5341c7dxxxx | 任务 ID。 |

#### 请求示例

```bash
curl --location --request POST 'https://qz.sii.edu.cn/openapi/v1/hpc_jobs/detail' \
  --header 'Authorization: Bearer xxxx' \
  --data-raw '{
    "job_id": "hpc-job-7768776e-16b5-4b09-a61e-e5341c7dxxxx"
  }'
```

#### 返回参数

| 参数 | 类型 | 示例值 | 描述 |
| --- | --- | --- | --- |
| code | Integer | 0 | 错误代码。0 表示成功，非 0 表示发生错误。 |
| message | String | 错误信息 | 错误信息。 |

### 6.3 停止高性能计算任务

#### 请求说明

- 请求方式：`POST`。
- 请求地址：`https://qz.sii.edu.cn/openapi/v1/hpc_jobs/stop`。

#### 请求参数

| 参数 | 类型 | 是否必选 | 示例值 | 描述 |
| --- | --- | --- | --- | --- |
| job_id | String | 是 | hpc-job-ccbf7e37-f28e-4eef-8fbe-ee6f04d3xxxx | 任务 ID。 |

#### 请求示例

```bash
curl --location --request POST 'https://qz.sii.edu.cn/openapi/v1/hpc_jobs/stop' \
  --header 'Authorization: Bearer xxxx' \
  --data-raw '{
    "job_id": "hpc-job-ccbf7e37-f28e-4eef-8fbe-ee6f04d3xxxx"
  }'
```

#### 返回参数

| 参数 | 类型 | 示例值 | 描述 |
| --- | --- | --- | --- |
| code | Integer | 0 | 错误代码。0 表示成功，非 0 表示发生错误。 |
| message | String | 错误信息 | 错误信息。 |
