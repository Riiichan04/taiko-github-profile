# taiko-github-profile 🥁

[English](../README.md) | **Tiếng Việt**

Banner Taiko lặp để trang trí README, vẽ hoàn toàn bằng hình học. Render offline không cần trình duyệt, ảnh nguồn hay âm thanh.

![Bố cục gốc](../assets/taiko.gif)

## Dùng trong workflow profile

Để chạy thử, chép [workflow test thủ công](../examples/test-workflow.yml) vào `.github/workflows/test-taiko.yml` trong repo gọi Action và thay `OWNER` bằng chủ repo Action. Chọn **Actions → Try taiko-github-profile → Run workflow**, rồi tải artifact `taiko-preview`. Workflow này xuất SVG để xem thử, không publish nhánh output. Nếu GitHub từ chối token có sẵn, thêm repository secret `CONTRIBUTIONS_TOKEN` có quyền phù hợp.

Repo này đã có composite Action qua [action.yml](../action.yml). Repo profile chỉ gọi Action; code Python vẫn nằm ở đây. Mặc định xuất SVG. Workflow mẫu xuất hai nền và publish lên nhánh `output` ở bước riêng.

Chép [examples/profile-workflow.yml](../examples/profile-workflow.yml) vào repo profile, thay `OWNER/taiko-github-profile@main` sau khi đưa dự án này lên GitHub. Chưa có tag phiên bản Action nào được publish từ checkout local này.

```yaml
- name: Generate Taiko
  uses: OWNER/taiko-github-profile@main
  with:
    username: ${{ github.repository_owner }}
    github-token: ${{ secrets.GITHUB_TOKEN }}
    bpm: '120'
    outputs: |
      dist/taiko.svg?background=original&variant=full
      dist/taiko-festival.svg?background=festival&variant=full
```

Bước này chỉ render. Workflow đầy đủ được liên kết ở trên có checkout, lịch chạy, quyền và publish. `outputs` chọn định dạng theo đuôi file, cho phép tùy chỉnh hình ảnh từng dòng. GIF mặc định **30 FPS trong Action**; SVG chạy liên tục theo trình duyệt, không có FPS cố định. Các CLI GIF thủ công hiện mặc định **25 FPS**; thêm `--fps 30` nếu muốn cùng cấu hình. TJA custom giữ BPM riêng.

## Chạy nhanh

Cần Python 3.10 trở lên. Chạy tất cả lệnh dưới đây từ **thư mục gốc repo**, không phải thư mục `docs`.

```sh
python -m pip install -r requirements.txt
python scripts/render.py
```

Lệnh trên render [chart demo](../charts/demo.tja) thành `generated/renders/taiko.gif` và `generated/renders/taiko.png`: 800 × 220, 25 FPS, vòng lặp liền mạch 8 giây.

**Trạng thái hiện tại:** CLI render mặc định dùng `charts/demo.tja`. Beatmap contribution có thể tạo từ snapshot cục bộ hoặc dữ liệu GitHub GraphQL. Repo này chỉ chạy test; Action và workflow profile mẫu hỗ trợ publish theo lịch sau khi thiết lập.

## Bố cục và nền

- `--variant classic`: variant 1, 800 × 220, có khoảng nền trang trí.
- `--variant full`: variant 2, banner gọn 766 × 108, trống nhỏ hơn và đường nốt chiếm hết chiều cao.
- `--background original`: nền cam sọc chéo.
- `--background festival`: đỏ rượu, tia sáng, điểm vàng và họa tiết sóng.

![Bố cục gọn](../assets/taiko-full.gif)

![Nền lễ hội](../assets/taiko-festival.gif)

```sh
python scripts/render.py --variant full
python scripts/render.py --background festival
python scripts/render.py --variant full --background festival
```

| Bố cục | Nền gốc | Nền lễ hội |
| --- | --- | --- |
| Classic | `assets/taiko.gif` | `assets/taiko-festival.gif` |
| Full | `assets/taiko-full.gif` | `assets/taiko-full-festival.gif` |

Bảng trên liệt kê ảnh demo được giữ trong `assets/`. Render local mặc định xuất vào `generated/renders/`; mỗi GIF có một PNG xem trước cùng tên. Dùng CLI để tạo lại bốn tổ hợp bố cục và nền.

## Cách xây dựng beatmap contribution mặc định

Generator đọc contribution theo thứ tự ngày cũ → mới và xuất TJA cùng metadata. Bắt đầu với [examples/contributions.json](../examples/contributions.json), hoặc tự cung cấp snapshot:

```json
{"username":"your-username","days":[{"date":"2026-01-01","count":3},{"date":"2026-01-02","count":0}]}
```

```sh
python scripts/generate_contributions.py examples/contributions.json
python scripts/render.py --chart generated/contributions/contributions.tja --variant full --background festival --auto-spacing --output generated/contributions/taiko.gif
```

Generator mặc định dùng **120 BPM**, seed `default`, xuất `generated/contributions/contributions.tja` và `generated/contributions/contributions.meta.json`. Đổi tempo/seed bằng `--bpm 180 --seed your-seed` trong lệnh generate; đổi nơi lưu bằng `--output-directory generated/mine`.

### Dữ liệu và phân loại

Ngày không được trùng, số contribution phải là số nguyên không âm, cửa sổ dữ liệu dài 1–366 ngày lịch. Ngày thiếu giữa hai mốc được điền 0. Generator chưa tự lấy dữ liệu GitHub hay tự chọn cửa sổ một năm.

Chỉ **ngày có hoạt động** được dùng để tính percentile. Sắp số contribution tăng dần rồi lấy phần tử thứ `ceil(p × N)` với p = 0,8 hoặc 0,9. Các ngày bằng ngưỡng được xét như nhau, nên đồng hạng có thể làm nhóm chứa nhiều hơn đúng 10% hoặc 20% số ngày.

Áp dụng theo thứ tự dưới đây; mỗi ngày chỉ nhận một loại đoạn:

| Ưu tiên | Điều kiện | Kết quả |
| --- | --- | --- |
| Nghỉ | 0 contribution | Không có nốt; luôn ngắt streak |
| Drumroll | Thuộc nhóm top 10%, cao hơn trung vị ngày hoạt động, ít nhất 10 contribution và ít nhất 3 lần trung vị | Trong cụm ứng viên liên tiếp, chỉ ngày cao nhất thành roll; bằng nhau chọn ngày sớm hơn |
| Stream cao điểm | Thuộc nhóm top 20%, cao hơn trung vị, chưa được chọn làm roll | Đúng **N nốt liên tục** nếu ngày đó có N contribution; gồm cả ứng viên roll không được chọn |
| Stream streak | Ngày còn lại trong streak dài hơn 7 ngày hoạt động liên tiếp | Một nốt/ngày, chuỗi liên tục; không tự ngắt sau mỗi 5 nốt |
| Nốt thường | Ngày hoạt động còn lại | Don nếu không vượt trung vị; Ka nếu vượt trung vị |

Năm ngày nào cũng có cùng số contribution sẽ không tạo outlier hay roll, kể cả 365 ngày × 1 contribution. Luật streak vẫn áp dụng. Ngưỡng ít nhất 10 và hệ số 3 là mặc định tạm thời trong `Rules` ở [contributions.py](../scripts/taiko/contributions.py).

### Timing, khoảng nghỉ và roll

- Stream tự sinh không dùng kiểu spam 1/6. Khoảng tap là `84/190 beat`: khoảng 0,221 giây ở 120 BPM, vừa với nốt rộng 42 px chạy 190 px/giây. Đổi BPM làm khoảng thời gian tap thay đổi; `--auto-spacing` đổi tốc độ hiển thị để tránh đè nốt.
- Nghỉ dưới 7 ngày dùng khoảng tap bình thường cho mỗi ngày. Từ 7 ngày trở lên, thời lượng nghỉ là **số ngày / 7 giây**, độc lập BPM: 28 ngày = 4 giây; 30 ngày ≈ 4,286 giây. Khoảng nghỉ luôn ngắt streak.
- Roll có đúng N cú đánh mục tiêu. Phần roll dài `min(N / 20, 2)` giây, sau đó thêm một khoảng tap để đặt dấu kết thúc `8`. Animation mặt trống chạy ở 72% nhịp đánh, không sửa sự kiện trong chart.
- Seed SHA-256 phụ thuộc phiên bản generator, username, ngày và seed người dùng. Ngày mới ít contribution không reseed pattern ngày cũ. Phân loại có thể đổi nếu ngưỡng percentile thay đổi. Mẫu màu lặp không tạo nhóm 5 hay khoảng nghỉ nhân tạo.
- Không ép đủ 30 giây. Vượt giới hạn 100.000 nốt/cú đánh, 4096 beat hay 100.000 frame nguồn thì báo lỗi, không âm thầm cắt stream.

### Metadata và khả năng tái tạo

Giữ cặp `.tja` và `.meta.json` cùng nhau. Metadata lưu ngày/số contribution nguồn, cấu hình, seed, quyết định từng ngày và số cú đánh roll chính xác. Bộ đọc tự tải metadata và kiểm tra SHA-256 khớp với TJA.

Nếu sửa TJA tự sinh, cần tạo lại cặp file hoặc bỏ sidecar để dùng hành vi chart custom thông thường. Khi không có metadata, roll dùng mặc định 16 cú đánh/giây; cú pháp chuẩn `5...8` không lưu số cú đánh.

## Tự viết chart TJA

Để dùng TJA qua Action, commit file `charts/custom.tja` vào **repo gọi Action** (ví dụ repo profile), rồi thay bước tạo chart contribution bằng:

```yaml
- uses: actions/checkout@v6
- uses: OWNER/taiko-github-profile@main
  with:
    chart: charts/custom.tja
    outputs: |
      taiko/taiko.svg?background=original
      taiko/taiko-festival.svg?background=festival
```

Đường dẫn tính từ repo vừa checkout, không phải repo Action. Có `chart` thì bỏ qua fetch contribution và tạo chart tự động, không cần token API contribution. BPM lấy từ TJA, không bị input `bpm` của Action ghi đè. Không kết hợp `chart` với `snapshot`. Giữ bước commit ảnh hiện tại để publish kết quả. Chart đơn giản để thử:

```text
TITLE:Custom test
BPM:120
#START
1212,
11221122,
50000008,
0000,
#END
```

Dùng [charts/demo.tja](../charts/demo.tja) làm ví dụ cơ bản. [charts/patterns.tja](../charts/patterns.tja) minh họa stream, trộn nhịp, 1/6 và nghỉ. Chart custom vẫn có thể dùng 1/6 dù generator contribution không sinh kiểu này.

- `0`: nghỉ; `1`: Don; `2`: Ka; `5`: bắt đầu drumroll; `8`: kết thúc.
- Dấu phẩy kết thúc ô nhịp, xuống dòng thì không. Một dấu phẩy trống là cả ô nhịp nghỉ.
- Với 4/4: 4 vị trí cho khoảng cách một beat, 16 cho 1/4 beat, 24 cho 1/6 beat.
- Bỏ qua khoảng trắng và chú thích `//`.

Hỗ trợ UTF-8/BOM, một course mỗi file, BPM cố định 30–300, `#START`, `#END` và `#MEASURE` giữa các ô nhịp. Chấp nhận metadata `WAVE`/`OFFSET` nhưng không phát nhạc hay áp offset âm thanh. Chưa hỗ trợ đổi BPM, lệnh scroll, phân nhánh, nốt lớn và balloon; sẽ báo file/dòng khi gặp tính năng chưa hỗ trợ.

```sh
python scripts/render.py --chart path/to/custom.tja --speed 190
python scripts/render.py --chart path/to/custom.tja --auto-spacing --note-gap 4 --output generated/renders/custom.gif
```

`--speed` nhận 50–1000 px/giây. `--auto-spacing` ghi đè tốc độ bằng một giá trị cố định tính từ cặp tap gần nhất, kể cả điểm nối vòng lặp, và đường kính nốt 42 px. `--note-gap 4` chừa khe 4 px cho cặp gần nhất. Không tính roll; đoạn thưa vẫn xa hơn. Tự căn không sửa BPM/timing; chart dày có thể chạy rất nhanh. TJA tự viết không bắt buộc có metadata.

TJA là định dạng chart đầu vào. JSON snapshot contribution và metadata có mục đích khác.

## Chất lượng GIF, kiểm tra và benchmark

Exporter chuẩn bị scene một lần, chỉ xét nốt trong vùng nhìn, cache cả hai nền, chuyển mỗi frame sang bảng màu ngay, gộp frame giống nhau thành thời gian giữ và bật nén GIF. Timing theo đơn vị 10 ms của GIF, không cộng dồn sai số từng frame. Khoảng giữ hơn 655,35 giây được chia nhỏ mà không đổi pixel; nhánh này ghi frame đầy đủ để tránh encoder tự gộp lại. Chỉ thay file GIF đích sau khi encode thành công.

```sh
python scripts/render.py --chart charts/demo.tja --fps 25 --colors 96
python scripts/render.py --chart charts/demo.tja --fps 15 --colors 64 --output generated/renders/smaller.gif
python -m unittest discover -s tests -v
python benchmarks/run.py
```

Giảm FPS/số màu là tùy chọn đánh đổi chất lượng, không phải mặc định. [benchmarks/report.json](../benchmarks/report.json) so sánh hai exporter trên cùng renderer đã chuẩn bị, chart 16 giây, 25 FPS và 96 màu: lần đo Windows ghi nhận GIF nhẹ hơn **21%**, RAM đỉnh giảm **68,7%**, thời gian xuất tăng **15,5%**. Kết quả phụ thuộc fixture; bản exporter cũ được giữ để đo lại.

## GitHub Actions và nhúng README

[Workflow test](../.github/workflows/test-action.yml) chạy bộ test offline khi push hoặc mở pull request có thay đổi liên quan. Có thể chạy thủ công qua **Actions → Test taiko-github-profile → Run workflow**. Workflow chỉ cần quyền đọc repo.

Để cập nhật ảnh demo, chạy CLI render local rồi tự commit asset đã chọn. Muốn xuất animation contribution hằng ngày và publish nhánh output, dùng [workflow profile mẫu](../examples/profile-workflow.yml); workflow đó cần checkout và quyền `contents: write`.

Để nhúng ảnh ở repo khác, thay `OWNER/REPO` và tên nhánh:

```md
![Taiko](https://raw.githubusercontent.com/OWNER/REPO/main/assets/taiko.gif)
```

## Lấy contribution thật từ GitHub

Cấu hình `GH_TOKEN` hoặc `GITHUB_TOKEN` trong biến môi trường, rồi chạy:

```sh
python scripts/github_contributions.py your-username --bpm 200 --output generated/github-your-username/taiko.gif
```

Lệnh lấy **365 ngày lịch UTC, gồm cả hôm nay**, sau đó tạo snapshot, TJA/metadata và GIF. Contribution hôm nay là số tại lúc fetch, có thể tăng ở lần chạy sau. Ngày UTC đổi lúc 07:00 giờ Việt Nam; không dùng múi giờ local của runner để chọn cửa sổ. `--end-date` nhận hôm nay hoặc ngày trước đó theo UTC, không nhận ngày tương lai. Mặc định render dùng bố cục gọn, nền lễ hội và tự căn khoảng cách nốt. Token chỉ được đọc từ môi trường, không lưu vào snapshot hay truyền trong tham số lệnh. Số liệu phụ thuộc quyền của token và cài đặt riêng tư của profile; contribution riêng tư có thể khác lịch công khai.

```sh
python scripts/github_contributions.py your-username --days 365 --end-date 2026-10-28 --fetch-only
python scripts/github_contributions.py your-username --bpm 180 --fps 15 --colors 64 --output generated/renders/github-smaller.gif
```

File sinh ra mặc định nằm ở `generated/github-USERNAME/`; có thể đổi bằng `--output-directory`. Client chia truy vấn GraphQL theo cửa sổ ngày nhỏ, kiểm tra đủ từng ngày, từ chối dữ liệu lỗi/thiếu, thử lại khi có lỗi mạng/server tạm thời và không tự đổi lỗi thành ngày 0 contribution. Lỗi fetch giữ nguyên GIF thành công trước đó. Luôn bật kiểm tra chứng chỉ TLS.

Trên GitHub Actions, dùng [workflow profile mẫu](../examples/profile-workflow.yml). Nếu GitHub từ chối truy cập contribution hoặc cần quyền nhìn dữ liệu khác, thêm repository secret `CONTRIBUTIONS_TOKEN`. Xem [xác thực GitHub](https://docs.github.com/en/graphql/guides/forming-calls-with-graphql). Không gửi token vào chat, source hay ô nhập workflow.

Nếu cần tải artifact, thêm bước upload-artifact vào workflow của bạn. Artifact không phải URL ảnh README cố định; dùng nhánh output của workflow profile để có URL ổn định.

Thay `your-username` trong lệnh bằng username GitHub của bạn. Ảnh mẫu đi kèm dùng **lịch HTML công khai đã chụp trước đó**, không phải dữ liệu trực tiếp của tài khoản placeholder. Cần token để kiểm chứng GraphQL thật; các test client dùng phản hồi mô phỏng, tách biệt với ảnh từ lịch công khai này.

## SVG động thử nghiệm

Bộ xuất vector gọn giữ timing TJA và tốc độ chạy, gồm metadata roll và nhịp visual mặt trống 72%. File dùng animation SVG khai báo, tái sử dụng hình nốt, không có JavaScript, tài nguyên ngoài hay frame raster nhúng.

```sh
python scripts/render_svg.py --chart generated/github-your-username/contributions.tja --auto-spacing --output generated/github-your-username/taiko.svg
```

[Tải SVG mẫu đi kèm](../assets/github-your-username-public-200bpm.svg). Đây là ví dụ từ lịch công khai đã chụp, không phải dữ liệu trực tiếp của `your-username`. Trình xem tĩnh có thể chỉ hiện frame đầu. Action hỗ trợ `variant=full` và `variant=classic`; CLI SVG riêng hiện xuất bố cục gọn. Hình SVG mô phỏng thiết kế raster, không khớp từng pixel.

Để thử trong README sau khi đưa asset lên repo:

```md
![Taiko](assets/github-your-username-public-200bpm.svg)
```

## Tổ chức asset

- `assets/`: chỉ giữ demo dùng trong README (bốn cặp GIF/PNG) và SVG contribution hiện tại. Xem [assets/README.md](../assets/README.md).
- `generated/`: snapshot, TJA/metadata và ảnh render local. Xem [generated/README.md](../generated/README.md).
- `generated/previews/`: các bản thử cũ được chuyển nguyên từ `assets/`; manifest ghi đường dẫn trước đó. Các file này chỉ lưu local, được Git bỏ qua.

CLI bình thường ghi vào `generated/`. Dùng `--output assets/name.svg` hoặc `--output assets/name.gif` để cập nhật bản mẫu được chọn rồi tự commit. CI của repo chỉ chạy test; publish profile được thiết lập riêng.

## Cấu trúc mã nguồn

`scripts/render.py` là CLI render; `scripts/generate_contributions.py` là CLI tạo chart offline. Các phần trong `scripts/taiko/`:

| File | Vai trò |
| --- | --- |
| `config.py` | Kích thước, FPS và màu dùng chung |
| `chart.py` | Đọc và kiểm tra TJA |
| `drawing.py` | Hàm vẽ hình có supersampling |
| `backgrounds.py` | Nền gốc và lễ hội |
| `drum.py` | Hình trống và phản hồi Don/Ka |
| `highway.py` | Đường nốt, điểm đánh và chỉ báo nhịp |
| `renderer.py` | Chuẩn bị scene và ghép bố cục |
| `export.py` | Encode GIF, bảng màu và PNG xem trước |
| `spacing.py` | Tự tính tốc độ chạy |
| `contributions.py` | Luật contribution offline và tạo TJA |
| `metadata.py` | Kiểm tra sidecar, khôi phục số cú đánh roll |
| `github.py` | Client lịch contribution GraphQL có xác thực |
| `svg.py` | Ghép SVG động và timing |
| `action_options.py` | Đọc và kiểm tra query tùy chọn từng file Action |
| `publish.py` | Publish một file theo cấu hình Action cũ |
| `svg_backgrounds.py` | Hàm nền SVG gốc/lễ hội riêng biệt |
| `svg_notes.py` | Định nghĩa hình Don/Ka và đặt nốt |
| `svg_elements.py` | Hàm tạo phần tử SVG và định dạng số dùng chung |
