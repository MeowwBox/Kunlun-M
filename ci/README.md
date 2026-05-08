## CI 配置文件目录

本目录用于集中存放 Kunlun-M 的 CI 示例配置，便于在其它项目中复用与维护。

注意：不同平台对配置文件路径有硬性要求：

- GitHub Actions 必须位于 `.github/workflows/*.yml`
- GitLab CI 默认入口必须是仓库根目录的 `.gitlab-ci.yml`（可通过 include 引入本目录文件）
- Jenkins 默认入口通常是仓库根目录的 `Jenkinsfile`（也可以在 Job 配置里把 Script Path 指向本目录文件）

