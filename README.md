# mc-redstone-music skill
把歌曲变成原版 Java 版 MC 可播放的 mcfunction 红石音乐。
安装：将整个 mc-redstone-music/ 目录放入你的 skills 目录（或把 SKILL.md 内容粘贴进系统提示）。
使用：对 AI 说"用 mc-redstone-music 把这首歌做成红石音乐"，它会先问版本/音轨/交付方式。
依赖：python3（仅 scripts 用；无代码环境时 AI 按 format_spec.md 手工生成）。
参考验证：生成器算法对 lemon 参考包（970 个 mcfunction）逆向并逐文件比对校正。
示例：examples/datapack_demo/ 内有可直接安装的独立示例数据包（真实曲目前奏节选）与 song.json 节选。
实战经验：references/midi_notes.md —— 真实 MIDI 解析坑、BPM 对齐验证、混音音量表、#speed=80 约定、PowerShell 5.1 注意事项。

