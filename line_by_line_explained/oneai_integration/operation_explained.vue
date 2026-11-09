<!-- ==============================================================================
     GIAO DIỆN ONEAI MEP OPERATION - GIẢI THÍCH CHI TIẾT TỪNG DÒNG (LINE-BY-LINE)
     Đường dẫn tương ứng: oneai_integration/frontend/operation/tab/operation.vue
     Chuẩn hóa 100% theo kiến trúc OneAI SDV Plugin
     Đặc điểm kỹ thuật:
       - Header 5 thẻ KPI thống kê toàn cục tương tác (Click-to-Filter)
       - Thanh Toolbar lọc theo Tháng TT, Trạng thái, Từ khóa tìm kiếm
       - Thanh Action Bar với thứ tự UX chuẩn: Reload, Insert, Save, Export, Delete
       - Bảng dữ liệu El-Table hỗ trợ Inline Editing, Cascading Dropdown Group/Part
       - Modal xem chi tiết kết quả đối soát tức thì (< 5ms) với 4 Tabs:
           + Tab 1: Danh sách lỗi sai lệch định lượng
           + Tab 2: Đối chiếu chi tiết theo từng Bản vẽ CAD
           + Tab 3: Thư viện soi ảnh trích xuất & Lightbox
           + Tab 4: Nhật ký tiến trình AI thời gian thực
       - Khối phê duyệt Kỹ sư dạng Grid 2 cột cân đối + 1 hàng nút bấm tinh gọn:
           + Cột 1: Người phê duyệt (Hiển thị Tên đầy đủ kèm Knox ID)
           + Cột 2: Ghi chú giải trình (Textarea)
           + Tự động lưu Knox ID vào cột REVIEW_BY trong Oracle DB
     ============================================================================== -->
<template>
  <div class="mep-container">
    <!-- ====================================================================
         1. KHỐI THẺ KPI THỐNG KÊ TOÀN CỤC (5 THẺ TƯƠNG TÁC CLICK-TO-FILTER)
         ==================================================================== -->
    <div class="kpi-cards-grid">
      <!-- Thẻ 1: Tổng số hồ sơ trong tháng -->
      <div class="kpi-card" :class="{ active: activeKpiFilter === 'ALL' }" @click="handleKpiFilter('ALL')">
        <div class="kpi-icon total"><i class="bi bi-stack"></i></div>
        <div class="kpi-info">
          <div class="kpi-val">{{ kpiStats.total }}</div>
          <div class="kpi-label">Tổng số hồ sơ</div>
        </div>
      </div>

      <!-- Thẻ 2: Hồ sơ Khớp 100% (Hoàn thành và không phát hiện sai lệch) -->
      <div class="kpi-card" :class="{ active: activeKpiFilter === 'OK' }" @click="handleKpiFilter('OK')">
        <div class="kpi-icon ok"><i class="bi bi-check2-circle"></i></div>
        <div class="kpi-info">
          <div class="kpi-val text-success">{{ kpiStats.ok }}</div>
          <div class="kpi-label">Khớp 100% (0 lỗi)</div>
        </div>
      </div>

      <!-- Thẻ 3: Hồ sơ Có sai lệch (Cần kỹ sư rà soát giải trình) -->
      <div class="kpi-card" :class="{ active: activeKpiFilter === 'ERR' }" @click="handleKpiFilter('ERR')">
        <div class="kpi-icon err"><i class="bi bi-exclamation-triangle"></i></div>
        <div class="kpi-info">
          <div class="kpi-val text-danger">{{ kpiStats.err }}</div>
          <div class="kpi-label">Có sai lệch</div>
        </div>
      </div>

      <!-- Thẻ 4: Hồ sơ Đang đối soát ngầm bằng AI Worker -->
      <div class="kpi-card" :class="{ active: activeKpiFilter === 'RUNNING' }" @click="handleKpiFilter('RUNNING')">
        <div class="kpi-icon running"><i class="bi bi-gear-wide-connected"></i></div>
        <div class="kpi-info">
          <div class="kpi-val text-warning">{{ kpiStats.running }}</div>
          <div class="kpi-label">Đang đối soát AI</div>
        </div>
      </div>

      <!-- Thẻ 5: Hồ sơ Chờ xử lý / Mới tạo -->
      <div class="kpi-card" :class="{ active: activeKpiFilter === 'WAITING' }" @click="handleKpiFilter('WAITING')">
        <div class="kpi-icon waiting"><i class="bi bi-hourglass-split"></i></div>
        <div class="kpi-info">
          <div class="kpi-val text-muted">{{ kpiStats.waiting }}</div>
          <div class="kpi-label">Chờ duyệt / Mới</div>
        </div>
      </div>
    </div>

    <!-- 2. THANH TÌM KIẾM & BỘ LỌC (TOP FILTER FLUID RESPONSIVE) -->
    <div class="toolbar">
      <el-select v-model="selectedStatus" placeholder="Chọn Trạng Thái" clearable class="toolbar-select">
        <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
      </el-select>

      <el-date-picker v-model="selectedMonth" type="month" placeholder="Chọn Tháng Thanh Toán" value-format="YYYY-MM"
        class="toolbar-date" />

      <el-input v-model="searchKeyword" placeholder="Nhập số WO hoặc tên công việc..." clearable class="toolbar-search"
        @keyup.enter="handleReload" />
    </div>

    <!-- 3. THANH CÔNG CỤ QUẢN TRỊ BẢNG (ACTION BAR THEO THỨ TỰ & MÀU SẮC UX CHUẨN) -->
    <div class="table-action-bar">
      <div class="total-count">
        <i class="bi bi-layers text-primary me-1"></i> Total: <span class="count-number">{{ total }} rows</span>
      </div>

      <div class="action-buttons">
        <!-- 1. NÚT RELOAD (LÀM MỚI BẢNG) -->
        <el-button :size="buttonSize" class="btn-reload" :loading="isLoading" @click="handleReload">
          <i class="bi bi-arrow-repeat me-1"></i> Reload
        </el-button>

        <!-- 2. NÚT INSERT (THÊM DÒNG MỚI VÀO CUỐI BẢNG) -->
        <el-button :size="buttonSize" class="btn-insert" @click="handleInsert">
          <i class="bi bi-plus-circle me-1"></i> Insert
        </el-button>

        <!-- 3. NÚT SAVE (LƯU VÀO DB - NÚT CHÍNH NỔI BẬT NHẤT) -->
        <el-button type="primary" :size="buttonSize" class="btn-save" :loading="isSaving" @click="handleSave">
          <i class="bi bi-floppy me-1"></i> Save
        </el-button>

        <!-- 4. NÚT EXPORT (.CSV) -->
        <el-button :size="buttonSize" class="btn-export" @click="handleExportCsv">
          <i class="bi bi-box-arrow-in-down me-1"></i> Export (.csv)
        </el-button>

        <!-- VẠCH NGĂN CÁCH NHẸ TRÁNH BẤM NHẦM NÚT XÓA -->
        <span class="btn-divider"></span>

        <!-- 5. NÚT DELETE (XÓA DÒNG - ĐẶT Ở CUỐI CÙNG, MÀU ĐỎ CẢNH BÁO) -->
        <el-button type="danger" :size="buttonSize" class="btn-delete" :disabled="selectedRows.length === 0"
          @click="handleDelete">
          <i class="bi bi-dash-circle me-1"></i> Delete
        </el-button>
      </div>
    </div>

    <!-- 4. BẢNG DỮ LIỆU ĐỐI SOÁT (TABLE GRID HỖ TRỢ INLINE EDIT & STICKY COLUMNS) -->
    <div class="table-container">
      <el-table ref="tableRef" :data="tableData" border height="660" size="small" style="width: 100%"
        show-overflow-tooltip empty-text="Không có dữ liệu đối soát" @selection-change="handleSelectionChange">
        <!-- CỘT CHECKBOX CHỌN DÒNG (STICKY LEFT) -->
        <el-table-column type="selection" width="45" align="center" fixed="left" />

        <!-- CỘT STT (STICKY LEFT) -->
        <el-table-column prop="STT" label="STT" width="55" align="center" fixed="left" />

        <!-- CỘT: SỐ CÔNG VIỆC (SỐ WO) - STICKY LEFT GIÚP KỸ SƯ LUÔN THEO DÕI ĐƯỢC MÃ WO KHI CUỘN NGANG -->
        <el-table-column prop="KEYID" label="SỐ CÔNG VIỆC (WO)" width="165" sortable align="center" fixed="left">
          <template #default="{ row }">
            <el-input v-if="row.isNew" v-model="row.KEYID" placeholder="Nhập số WO..." size="mini"
              class="inline-input" />
            <span v-else class="font-bold font-mono" style="color: #38BDF8;">{{ row.KEYID }}</span>
          </template>
        </el-table-column>

        <!-- Cột 4: Tên công việc / Hạng mục thi công (Bấm đúp chuột để sửa) -->
        <el-table-column prop="TASK_NAME" label="TÊN CÔNG VIỆC" min-width="260">
          <template #default="{ row }">
            <el-input v-if="row.isNew || row.isEditing" v-model="row.TASK_NAME" placeholder="Tên công việc..."
              size="mini" class="inline-input" />
            <span v-else class="cell-text" @dblclick="row.isEditing = true" title="Bấm đúp chuột để chỉnh sửa">{{
              row.TASK_NAME || '-' }}</span>
          </template>
        </el-table-column>

        <!-- Cột 5: Tháng thanh toán (YYYY-MM, tự động dời MinIO folder khi sửa) -->
        <el-table-column prop="PAYMENT_MONTH" label="THÁNG TT" width="115" align="center" sortable>
          <template #default="{ row }">
            <el-input v-if="row.isNew || row.isEditing" v-model="row.PAYMENT_MONTH" placeholder="YYYY-MM" size="mini"
              :disabled="row.STATUS === 'RUNNING'" class="inline-input" />
            <span v-else class="cell-text" :class="{ 'cursor-not-allowed': row.STATUS === 'RUNNING' }"
              @dblclick="row.STATUS !== 'RUNNING' && (row.isEditing = true)"
              :title="row.STATUS === 'RUNNING' ? 'Không thể đổi tháng khi AI đang chạy' : 'Bấm đúp chuột để chỉnh sửa'">
              {{ row.PAYMENT_MONTH || '-' }}
            </span>
          </template>
        </el-table-column>

        <!-- Cột 6: Người phụ trách (PIC) -->
        <el-table-column prop="PIC" label="NGƯỜI PHỤ TRÁCH" width="130" align="center">
          <template #default="{ row }">
            <el-input v-if="row.isNew || row.isEditing" v-model="row.PIC" placeholder="PIC..." size="mini"
              class="inline-input" />
            <span v-else class="cell-text" @dblclick="row.isEditing = true" title="Bấm đúp chuột để chỉnh sửa">{{
              row.PIC || '-' }}</span>
          </template>
        </el-table-column>

        <!-- Cột 7: Khối phòng ban (GROUP - Chọn Group để lọc Part tương ứng) -->
        <el-table-column prop="GROUP_NAME" label="GROUP" width="160" align="center">
          <template #default="{ row }">
            <el-select v-if="row.isNew || row.isEditing" v-model="row.GROUP_NAME" placeholder="Chọn Group..."
              size="mini" filterable clearable @change="onGroupChange(row)">
              <el-option v-for="g in groupOptions" :key="g.value" :label="g.label" :value="g.value" />
            </el-select>
            <span v-else class="cell-text" @dblclick="row.isEditing = true" title="Bấm đúp chuột để chỉnh sửa">
              {{ row.GROUP_NAME || '-' }}
            </span>
          </template>
        </el-table-column>

        <!-- Cột 8: Bộ phận (PART - Tự động thay đổi danh sách tùy theo Group đã chọn) -->
        <el-table-column prop="PART_NAME" label="PART" width="170" align="center">
          <template #default="{ row }">
            <el-select v-if="row.isNew || row.isEditing" v-model="row.PART_NAME"
              :placeholder="row.GROUP_NAME ? 'Chọn Part...' : 'Chọn Group trước'" size="mini" filterable clearable>
              <el-option v-for="p in getPartsByGroup(row.GROUP_NAME)" :key="p.value" :label="p.label"
                :value="p.value" />
            </el-select>
            <span v-else class="cell-text" @dblclick="row.isEditing = true" title="Bấm đúp chuột để chỉnh sửa">
              {{ row.PART_NAME || '-' }}
            </span>
          </template>
        </el-table-column>

        <!-- Cột 9: Trạng thái (STATUS) kèm thanh % tiến độ xử lý -->
        <el-table-column prop="STATUS" label="TRẠNG THÁI" width="135" align="center" sortable>
          <template #default="{ row }">
            <el-tag v-if="row.STATUS === 'COMPLETED'" type="success" effect="light">Hoàn Tất</el-tag>
            <div v-else-if="row.STATUS === 'RUNNING'" class="progress-cell">
              <el-tag type="warning" effect="dark" size="mini">Đang Xử Lý</el-tag>
              <el-progress :percentage="Number(row.PROGRESS) || 0" :stroke-width="6" :show-text="true"
                class="progress-bar-inline" />
            </div>
            <el-tag v-else-if="row.STATUS === 'WAITING'" type="info">Chờ Duyệt</el-tag>
            <el-tag v-else-if="row.STATUS === 'CANCEL'" type="danger">Thất Bại</el-tag>
            <el-tag v-else type="info">{{ row.STATUS || 'Mới' }}</el-tag>
          </template>
        </el-table-column>

        <!-- Cột 10: Tải lên tài liệu đính kèm (File Excel dự toán) -->
        <el-table-column label="TÀI LIỆU ĐÍNH KÈM" width="135" align="center">
          <template #default="{ row }">
            <el-upload :show-file-list="false" :auto-upload="false" accept=".xlsx,.xlsm"
              :on-change="(file) => handleUploadExcel(file, row)" :disabled="row.STATUS === 'RUNNING' || row.isNew">
              <el-button class="btn-upload-file" :size="buttonSize" :loading="row.STATUS === 'RUNNING'"
                :disabled="row.STATUS === 'RUNNING' || row.isNew">
                <i v-if="row?.STATUS !== 'RUNNING'" class="bi bi-cloud-arrow-up me-1"></i>
                {{ row.STATUS === 'RUNNING' ? 'Đang chạy...' : 'Upload' }}
              </el-button>
            </el-upload>
          </template>
        </el-table-column>

        <!-- Cột 11: Kết quả kiểm tra (Bấm vào Badge để mở Modal xem chi tiết tức thì) -->
        <el-table-column label="KẾT QUẢ KIỂM TRA" width="150" align="center">
          <template #default="{ row }">
            <div v-if="row.STATUS === 'COMPLETED'">
              <el-tag :type="Number(row.ERROR_COUNT) === 0 ? 'success' : 'danger'" effect="light"
                class="cursor-pointer result-tag-badge" :title="`Bấm để xem chi tiết đối soát ${row.KEYID}`"
                @click="openDetailModal(row)">
                {{ Number(row.ERROR_COUNT) === 0 ? '✅ Khớp 100%' : `❌ Lệch ${row.ERROR_COUNT} lỗi` }}
              </el-tag>
            </div>
            <div v-else-if="row.STATUS === 'RUNNING'" style="color: #E6A23C; font-size: 11px;">
              <i class="el-icon-loading"></i> Đang đối soát...
            </div>
            <div v-else-if="row.STATUS === 'CANCEL'">
              <el-tag type="danger" size="mini" class="cursor-pointer" @click="openDetailModal(row)">
                ❌ Lỗi xử lý
              </el-tag>
            </div>
            <span v-else style="color: #909399;">-</span>
          </template>
        </el-table-column>

        <!-- CỘT: CHI TIẾT BÁO CÁO & DUYỆT (STICKY RIGHT GIÚP THAO TÁC DUYỆT / TẢI BÁO CÁO TỨC THÌ) -->
        <el-table-column label="CHI TIẾT BÁO CÁO" width="180" align="center" fixed="right">
          <template #default="{ row }">
            <div v-if="row.STATUS === 'COMPLETED'">
              <!-- Hiển thị kết quả duyệt đã lưu trong Database -->
              <div>
                <el-tag v-if="row.REVIEW_DECISION === 'APPROVED'" type="success" size="mini"
                  :title="row.REVIEW_BY ? `Duyệt bởi: ${row.REVIEW_BY}` : ''">
                  Đã Duyệt
                </el-tag>
                <el-tag v-else-if="row.REVIEW_DECISION === 'REJECTED'" type="danger" size="mini"
                  :title="row.REVIEW_BY ? `Từ chối bởi: ${row.REVIEW_BY}` : ''">
                  Từ Chối
                </el-tag>
                <div v-else style="display: inline-flex; gap: 4px;">
                  <el-button type="success" size="mini" @click="handleReview(row, 'APPROVED')">Duyệt</el-button>
                  <el-button type="danger" size="mini" @click="handleReview(row, 'REJECTED')">Hủy</el-button>
                </div>
              </div>

              <!-- Nút tải file báo cáo nén ZIP -->
              <div v-if="row.RESULT_LINK" style="margin-bottom: 3px;">
                <el-button type="text" size="small" class="download-btn" @click="handleDownloadFile(row)">
                  📥 Tải Báo Cáo (.zip)
                </el-button>
              </div>
            </div>
            <span v-else style="color: #909399;">-</span>
          </template>
        </el-table-column>

        <!-- Cột 13: Thời gian tải file lên -->
        <el-table-column prop="UPLOAD_TIME" label="THỜI GIAN TẢI LÊN" width="145" align="center" sortable>
          <template #default="{ row }">
            <span class="text-muted font-mono" style="font-size: 11px;">{{ row.UPLOAD_TIME || '-' }}</span>
          </template>
        </el-table-column>

        <!-- Cột 14: Thời gian hoàn tất có kết quả -->
        <el-table-column prop="RESULT_TIME" label="THỜI GIAN KẾT QUẢ" width="145" align="center" sortable>
          <template #default="{ row }">
            <span class="text-muted font-mono" style="font-size: 11px;">{{ row.RESULT_TIME || '-' }}</span>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- ====================================================================
         5. THANH ĐIỀU HƯỚNG PHÂN TRANG (PAGINATION)
         ==================================================================== -->
    <div class="pagination-container">
      <el-pagination :current-page="page" :page-size="pageSize" :page-sizes="[20, 50, 100]" :total="total"
        layout="total, sizes, prev, pager, next, jumper" @current-change="handlePageChange"
        @size-change="handleSizeChange" />
    </div>

    <!-- ====================================================================
         6. MODAL XEM CHI TIẾT KẾT QUẢ ĐỐI SOÁT & PHÊ DUYỆT (TASK DETAIL DIALOG)
         ==================================================================== -->
    <el-dialog v-model="showDetailDialog" :title="`Chi Tiết Đối Soát Hồ Sơ: ${currentTask?.KEYID || ''}`" width="85%"
      top="4vh" :close-on-click-modal="false" class="mep-detail-dialog" append-to-body>
      <div v-if="detailLoading" class="detail-loading-box">
        <i class="el-icon-loading" style="font-size: 32px; color: #409EFF;"></i>
        <p style="margin-top: 12px; color: #E5EAF3;">Đang tải và đồng bộ kết quả đối soát AI...</p>
      </div>

      <div v-else-if="currentDetail" class="detail-content-wrap">
        <!-- HEADER SUMMARY CARD -->
        <div class="detail-header-card">
          <div class="dh-title">
            <h3><i class="bi bi-file-earmark-spreadsheet text-primary me-2"></i>{{ currentTask?.TASK_NAME || 'Chưa đặt tên công việc' }}</h3>
            <div class="dh-meta">
              <span><b>Mã WO:</b> <span class="font-mono text-cyan" style="color: #38BDF8; font-weight: 700; background: rgba(56, 189, 248, 0.12); padding: 2px 8px; border-radius: 4px; border: 1px solid rgba(56, 189, 248, 0.25);">{{ currentTask?.KEYID }}</span></span>
              <span><b>PIC:</b> {{ currentTask?.PIC || '—' }}</span>
              <span><b>Phần việc:</b> {{ currentTask?.PART_NAME }} / {{ currentTask?.GROUP_NAME }}</span>
              <span><b>Tháng TT:</b> {{ currentTask?.PAYMENT_MONTH }}</span>
              <span><b>Công nghệ:</b> {{ currentDetail.mode }}</span>
            </div>
          </div>

        <!-- KHỐI 2: 4 THẺ THỐNG KÊ NHANH (METRIC TIÊU BIỂU) -->
        <div class="metric-tiles-row">
          <div class="m-stat" :class="currentDetail.error_count > 0 ? 'has-err' : 'all-ok'">
            <b>{{ currentDetail.error_count }}</b>
            <span>{{ currentDetail.error_count > 0 ? 'Vị trí sai lệch' : 'Lỗi phát hiện' }}</span>
          </div>
          <div class="m-stat">
            <b>{{ currentDetail.drawings_count }}</b>
            <span>Bản vẽ AI bóc tách</span>
          </div>
          <div class="m-stat">
            <b>{{ currentDetail.total_items }}</b>
            <span>Dòng vật tư kiểm tra</span>
          </div>
          <div class="m-stat">
            <b style="font-size: 15px; color: #409EFF;">{{ currentDetail.sheet }}</b>
            <span>Bảng danh mục nguồn</span>
          </div>
        </div>

        <!-- PHÂN LOẠI LỖI (ERROR BREAKDOWN BADGES) -->
        <div v-if="errorTypeEntries.length > 0" class="error-breakdown-row">
          <span class="breakdown-label">Phân loại sai lệch:</span>
          <el-tag v-for="[type, count] in errorTypeEntries" :key="type" type="danger" effect="light" class="me-2 mb-1">
            {{ type }}: <b>{{ count }}</b>
          </el-tag>
        </div>

        <!-- KHỐI 3: CÁC TAB CHI TIẾT ĐỐI SOÁT -->
        <el-tabs v-model="activeDetailTab" type="border-card" class="detail-tabs">
          <!-- TAB 1: DANH SÁCH LỖI PHÁT HIỆN -->
          <el-tab-pane name="errors">
            <template #label>
              <span><i class="bi bi-exclamation-triangle-fill text-danger me-1"></i> Danh Sách Lỗi ({{
                currentDetail.errors?.length || 0 }})</span>
            </template>
            <div v-if="!currentDetail.errors || currentDetail.errors.length === 0" class="clean-state-box">
              <i class="bi bi-check-circle-fill text-success" style="font-size: 42px;"></i>
              <h4>Tuyệt vời! Không phát hiện lỗi sai lệch nào</h4>
              <p class="text-muted">Tất cả số lượng vật tư giữa Dự toán nhà thầu và Bản vẽ thiết kế bóc tách khớp 100%.</p>
            </div>
            <el-table v-else :data="currentDetail.errors" border size="small" height="340" style="width: 100%">
              <el-table-column prop="id" label="#" width="50" align="center" />
              <el-table-column prop="type" label="Phân loại lỗi" width="160">
                <template #default="{ row }">
                  <el-tag type="danger" size="mini">{{ row.type }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="dwg" label="Bản vẽ" width="130" align="center" />
              <el-table-column prop="code" label="Mã SDAC" width="140" align="center">
                <template #default="{ row }"><b class="font-mono">{{ row.code }}</b></template>
              </el-table-column>
              <el-table-column prop="name" label="Tên vật tư" min-width="180" show-overflow-tooltip />
              <el-table-column prop="unit" label="ĐVT" width="65" align="center" />
              <el-table-column prop="vendor_qty" label="SL Dự toán" width="100" align="center" />
              <el-table-column prop="ai_qty" label="SL Bản vẽ (AI)" width="125" align="center">
                <template #default="{ row }">
                  <el-tooltip v-if="row.ai_breakdown" :content="`Bóc tách từ: ${row.ai_breakdown}`" placement="top">
                    <span class="font-bold text-primary cursor-pointer">
                      {{ row.ai_qty }} <i class="bi bi-info-circle ms-1" style="font-size: 11px;"></i>
                    </span>
                  </el-tooltip>
                  <span v-else class="font-bold">{{ row.ai_qty }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="diff" label="Chênh lệch" width="145" align="center">
                <template #default="{ row }">
                  <el-tag v-if="String(row.diff).includes('Thiếu') || String(row.diff).includes('Lệch')" type="danger" size="mini" effect="dark" style="font-weight: 700; border-radius: 4px;">
                    <i class="bi bi-arrow-down-right me-1"></i>{{ row.diff }}
                  </el-tag>
                  <el-tag v-else-if="String(row.diff).includes('Thừa')" type="warning" size="mini" effect="dark" style="font-weight: 700; border-radius: 4px;">
                    <i class="bi bi-arrow-up-right me-1"></i>{{ row.diff }}
                  </el-tag>
                  <span v-else class="text-danger font-bold">{{ row.diff }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="msg" label="Chi tiết đối chiếu" min-width="220" show-overflow-tooltip />
            </el-table>
          </el-tab-pane>

          <!-- TAB 2: ĐỐI CHIẾU THEO TỪNG BẢN VẼ -->
          <el-tab-pane name="drawings" lazy>
            <template #label>
              <span><i class="bi bi-diagram-3 me-1"></i> Đối Chiếu Theo Bản Vẽ ({{
                currentDetail.groups?.length || 0 }})</span>
            </template>
            <div v-if="!currentDetail.groups || currentDetail.groups.length === 0" class="p-4 text-center text-muted">
              Không có nhóm bản vẽ nào trong bảng kết quả.
            </div>
            <el-collapse v-else v-model="activeCollapseDrawings">
              <el-collapse-item v-for="(g, idx) in currentDetail.groups" :key="idx" :name="String(idx)">
                <template #title>
                  <div class="collapse-title-row">
                    <b>Bản vẽ: {{ g.drawing_no }}</b>
                    <span class="text-muted ms-3">({{ g.total_items }} vật tư)</span>
                    <el-tag v-if="g.error_count > 0" type="danger" size="mini" class="ms-2">
                      {{ g.error_count }} lỗi
                    </el-tag>
                    <el-tag v-else type="success" size="mini" class="ms-2">Khớp 100%</el-tag>
                  </div>
                </template>
                <el-table :data="g.rows || g.items || []" border size="mini" height="220" style="width: 100%">
                  <el-table-column prop="code" label="Mã vật tư" width="140" align="center">
                    <template #default="{ row }"><b class="font-mono">{{ row.code }}</b></template>
                  </el-table-column>
                  <el-table-column prop="name" label="Tên vật tư" min-width="180" show-overflow-tooltip />
                  <el-table-column prop="unit" label="ĐVT" width="65" align="center" />
                  <el-table-column prop="vendor_qty" label="SL Dự toán" width="100" align="center" />
                  <el-table-column prop="qty" label="SL Bản vẽ này" width="120" align="center">
                    <template #default="{ row }"><b class="text-primary">{{ row.qty }}</b></template>
                  </el-table-column>
                  <el-table-column prop="why" label="Kết quả đối chiếu" width="180" align="center">
                    <template #default="{ row }">
                      <span :class="row.ok ? 'text-success' : 'text-danger'">{{ row.why }}</span>
                    </template>
                  </el-table-column>
                </el-table>
              </el-collapse-item>
            </el-collapse>
          </el-tab-pane>

          <!-- TAB 3: SOI BẢN VẼ / ẢNH TRÍCH XUẤT -->
          <el-tab-pane name="images" lazy>
            <template #label>
              <span><i class="bi bi-images me-1"></i> Soi Bản Vẽ / Ảnh Trích Xuất ({{
                currentDetail.images?.length || 0 }})</span>
            </template>
            <div v-if="!currentDetail.images || currentDetail.images.length === 0" class="p-4 text-center text-muted">
              <i class="bi bi-image" style="font-size: 36px;"></i>
              <p style="margin-top: 10px;">Chưa có ảnh bản vẽ nào được lưu trong phiên này.</p>
            </div>
            <div v-else class="images-strip">
              <div v-for="(img, idx) in currentDetail.images" :key="idx" class="img-thumb-box">
                <el-image :src="getImgUrl(img.url)" :preview-src-list="previewImageList" :initial-index="idx"
                  fit="cover" class="thumb-img" loading="lazy" />
                <div class="img-name" :title="img.title || img.name">{{ img.title || img.name }}</div>
              </div>
            </div>
          </el-tab-pane>

          <!-- TAB 4: NHẬT KÝ TIẾN TRÌNH XỬ LÝ (LOGS) -->
          <el-tab-pane name="logs" lazy>
            <template #label>
              <span><i class="bi bi-terminal me-1"></i> Nhật Ký Xử Lý ({{ currentDetail.logs?.length || 0 }})</span>
            </template>
            <div class="logs-console">
              <div v-for="(line, idx) in currentDetail.logs" :key="idx" class="log-line">
                <span class="log-idx">{{ idx + 1 }}.</span> {{ line }}
              </div>
            </div>
          </el-tab-pane>
        </el-tabs>

        <!-- ====================================================================
             KHỐI 4: KHU VỰC PHÊ DUYỆT & HÀNH ĐỘNG (BỐ CỤC 2 CỘT + 1 HÀNG NÚT BẤM)
             ==================================================================== -->
        <div class="review-approval-card">
          <div class="review-card-header">
            <span class="review-title">
              <i class="bi bi-shield-check text-primary me-2"></i> KẾT LUẬN & PHÊ DUYỆT CỦA KỸ SƯ
            </span>
            <div v-if="currentTask?.REVIEW_DECISION" class="current-decision-badge">
              <span v-if="currentTask.REVIEW_DECISION === 'APPROVED'" style="color: #67C23A; background: rgba(103, 194, 58, 0.1); padding: 3px 8px; border-radius: 4px; border: 1px solid rgba(103, 194, 58, 0.3);">
                <i class="bi bi-check-circle-fill me-1"></i> Đã phê duyệt bởi: <b>{{ currentTask.REVIEW_BY }}</b>
                <span v-if="currentTask.REVIEW_NOTE" style="color: #CFD3DC; margin-left: 6px;">— "{{ currentTask.REVIEW_NOTE }}"</span>
              </span>
              <span v-else-if="currentTask.REVIEW_DECISION === 'REJECTED'" style="color: #F56C6C; background: rgba(245, 108, 108, 0.1); padding: 3px 8px; border-radius: 4px; border: 1px solid rgba(245, 108, 108, 0.3);">
                <i class="bi bi-x-circle-fill me-1"></i> Bị từ chối bởi: <b>{{ currentTask.REVIEW_BY }}</b>
                <span v-if="currentTask.REVIEW_NOTE" style="color: #CFD3DC; margin-left: 6px;">— "{{ currentTask.REVIEW_NOTE }}"</span>
              </span>
            </div>
          </div>

          <!-- GRID 2 CỘT CÂN ĐỐI: CỘT TRÁI NGƯỜI DUYỆT, CỘT PHẢI GHI CHÚ GIẢI TRÌNH -->
          <div class="review-grid-inputs">
            <!-- Cột trái: Người phê duyệt (Hiển thị Tên đầy đủ kèm Knox ID) -->
            <div class="review-col-user">
              <label class="review-field-label">👤 Người phê duyệt:</label>
              <el-input :model-value="loginUserDisplay || 'Kỹ sư MEP'" readonly class="readonly-input">
                <template #prefix>
                  <i class="bi bi-person-badge text-success"></i>
                </template>
              </el-input>
            </div>
            <!-- Cột phải: Ghi chú phê duyệt / giải trình -->
            <div class="review-col-note">
              <label class="review-field-label">📝 Ghi chú phê duyệt / giải trình:</label>
              <el-input 
                v-model="detailReviewNote"
                placeholder="Nhập ghi chú duyệt (VD: Lỗi số 2 đã đối soát hiện trường, nghiệm thu đạt...)" 
                clearable 
              />
            </div>
          </div>

          <!-- 1 HÀNG NÚT BẤM DUY NHẤT: BÊN TRÁI PHÊ DUYỆT, BÊN PHẢI THAO TÁC FILE -->
          <div class="review-actions-bar">
            <!-- Cụm hành động chính: Duyệt (Success) / Từ chối (Danger) -->
            <div class="review-main-btns">
              <el-button type="success" :size="buttonSize" @click="submitDetailReview('APPROVED')">
                <i class="bi bi-check-lg me-1"></i> Duyệt (Approve)
              </el-button>
              <el-button type="danger" :size="buttonSize" @click="submitDetailReview('REJECTED')">
                <i class="bi bi-x-lg me-1"></i> Từ Chối (Reject)
              </el-button>
            </div>

            <div class="spacer"></div>

            <!-- Cụm thao tác file & điều khiển modal -->
            <div class="review-sub-btns">
              <el-upload 
                :show-file-list="false" 
                :auto-upload="false" 
                accept=".xlsx,.xlsm"
                :on-change="(file) => handleUploadExcel(file, currentTask)" 
                :disabled="currentTask?.STATUS === 'RUNNING'"
                style="display: inline-block;"
              >
                <el-button :size="buttonSize" class="btn-upload-file" :loading="currentTask?.STATUS === 'RUNNING'">
                  <i v-if="currentTask?.STATUS !== 'RUNNING'" class="bi bi-cloud-arrow-up me-1"></i>
                  {{ currentTask?.STATUS === 'RUNNING' ? 'Đang chạy...' : 'Upload File Excel' }}
                </el-button>
              </el-upload>

              <el-button 
                v-if="currentTask?.RESULT_LINK" 
                :size="buttonSize" 
                type="primary" 
                plain
                @click="handleDownloadFile(currentTask)"
              >
                <i class="bi bi-cloud-arrow-down me-1"></i> Tải Báo Cáo (.zip)
              </el-button>

              <el-button 
                :size="buttonSize" 
                class="btn-rerun" 
                :loading="isRerunning || currentTask?.STATUS === 'RUNNING'"
                @click="handleRerun(currentTask)"
              >
                <i class="bi bi-arrow-clockwise me-1"></i> Chạy Lại AI
              </el-button>

              <el-button :size="buttonSize" @click="handleCloseDetailDialog">Đóng</el-button>
            </div>
          </div>
        </div>
      </div>

      <div v-else class="detail-loading-box">
        <i class="bi bi-exclamation-circle text-warning" style="font-size: 36px;"></i>
        <p style="margin-top: 12px; color: #E5EAF3;">Chưa có dữ liệu chi tiết cho hồ sơ này.</p>
        <el-button size="small" type="primary" @click="handleCloseDetailDialog">Đóng</el-button>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
// ==============================================================================
// KHỐI LOGIC VUE 3 COMPOSITION API
// ==============================================================================
import { ref, computed, onMounted, onUnmounted, watch, getCurrentInstance } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from 'axios'
import { get_total_row, get_data_page, save_mep_rows, delete_mep_rows, get_kpi_summary } from '../js/mepPayment'

// Dòng 601-620: Địa chỉ Worker API & Kích thước nút bấm (Tự động nhận diện Localhost vs Server Production/K8s)
const getFastApiBaseUrl = () => {
  if (typeof window !== 'undefined' && window.__FASTAPI_BASE_URL__) {
    return window.__FASTAPI_BASE_URL__
  }
  if (typeof process !== 'undefined' && process.env && process.env.VITE_FASTAPI_BASE_URL) {
    return process.env.VITE_FASTAPI_BASE_URL
  }
  if (typeof window !== 'undefined' && window.location) {
    const host = window.location.hostname
    if (host === 'localhost' || host === '127.0.0.1') {
      return 'http://127.0.0.1:8000'
    }
    // Khi chạy trên Server nội bộ / K8s: mặc định trỏ theo hostname của server cổng 8000
    return `${window.location.protocol}//${host}:8000`
  }
  return 'http://127.0.0.1:8000'
}
const FASTAPI_BASE_URL = getFastApiBaseUrl()
const buttonSize = ref('default')
const MAX_UPLOAD_SIZE_MB = 50 // Giới hạn file Excel upload tối đa 50MB

// ====================================================================
// THÔNG TIN TÀI KHOẢN ĐĂNG NHẬP ONEAI (THEO CHUẨN authStore / knoxId)
// ====================================================================
const _userInfo = ref(null)

const getUserInfo = () => {
  try {
    // 1. Lấy từ Vuex Store của OneAI qua component instance ($store.getters['authStore/userInfo'])
    const vm = getCurrentInstance()
    const appStore = vm?.appContext?.config?.globalProperties?.$store || vm?.proxy?.$store
    if (appStore?.getters && appStore.getters['authStore/userInfo']) {
      return appStore.getters['authStore/userInfo']
    }
  } catch (e) { }

  try {
    // 2. Lấy từ biến window.store toàn cục nếu nền tảng OneAI đưa ra window
    if (typeof window !== 'undefined' && window.store?.getters && window.store.getters['authStore/userInfo']) {
      return window.store.getters['authStore/userInfo']
    }
  } catch (e) { }

  try {
    // 3. Fallback: Lấy từ LocalStorage session của OneAI
    const cached = localStorage.getItem('userInfo') || localStorage.getItem('user')
    if (cached) {
      return JSON.parse(cached)
    }
  } catch (e) { }

  return null
}

// Knox ID & Tên người dùng OneAI (Tách bạch giữa hiển thị UI và lưu Database)
// 1. Tên hiển thị thân thiện trên UI (Ví dụ: "Nguyễn Văn Hùng")
const loginUserName = computed(() => {
  return _userInfo.value?.name || _userInfo.value?.knoxId || ''
})

// 2. Mã Knox ID dùng để lưu vào cột REVIEW_BY trong Database (Ví dụ: "vhung99.nguyen")
const loginKnoxId = computed(() => {
  return _userInfo.value?.knoxId || _userInfo.value?.userId || _userInfo.value?.userName || _userInfo.value?.name || ''
})

// 3. Chuỗi hiển thị đầy đủ kết hợp cả Tên và Knox ID (Ví dụ: "Nguyễn Văn Hùng (vhung99.nguyen)")
const loginUserDisplay = computed(() => {
  const name = _userInfo.value?.name
  const knox = _userInfo.value?.knoxId
  if (name && knox && name !== knox) {
    return `${name} (${knox})`
  }
  return name || knox || ''
})

// Giữ lại loginUser tương thích cho các nhãn UI
const loginUser = loginUserName

// Bộ lọc
const selectedStatus = ref('')
const selectedMonth = ref('')
const searchKeyword = ref('')
const statusOptions = [
  { label: 'Tất cả trạng thái', value: 'ALL' },
  { label: 'Chờ duyệt / Mới', value: 'WAITING' },
  { label: 'Đang xử lý', value: 'RUNNING' },
  { label: 'Hoàn tất', value: 'COMPLETED' },
  { label: 'Thất bại', value: 'CANCEL' }
]
const activeKpiFilter = ref('ALL')

// DANH MỤC PHÂN CẤP CỦA GROUP VÀ PART (CASCADING DROPDOWN)
const groupOptions = [
  { label: 'MES', value: 'MES Group' },
  { label: 'Infra', value: 'Infra Group' },
  { label: 'ESH', value: 'ESH Group' }
]

const partMapping = {
  'MES Group': [
    { label: 'MOS', value: 'MOS' },
    { label: 'IT Governance', value: 'IT Governance' },
    { label: 'Data Analysis', value: 'Data Analysis' },
    { label: 'AI Transformation', value: 'AI Transformation' }
  ],
  'Infra Group': [
    { label: 'Clean Room Technology', value: 'Clean Room Technology' },
    { label: 'Infra Operation', value: 'Infra Operation' },
    { label: 'Infra Technology', value: 'Infra Technology' },
    { label: 'IRP', value: 'IRP' },
    { label: 'Construction', value: 'Construction' }
  ],
  'ESH Group': [
    { label: 'Safety', value: 'Safety' },
    { label: 'Disaster Prevention', value: 'Disaster Prevention' },
    { label: 'Enviroment', value: 'Enviroment' },
    { label: 'Health', value: 'Health' }
  ]
}

const defaultParts = [
  { label: 'MOS', value: 'MOS' },
  { label: 'IT Governance', value: 'IT Governance' },
  { label: 'Data Analysis', value: 'Data Analysis' },
  { label: 'AI Transformation', value: 'AI Transformation' },
  { label: 'Clean Room Technology', value: 'Clean Room Technology' },
  { label: 'Infra Operation', value: 'Infra Operation' },
  { label: 'Infra Technology', value: 'Infra Technology' },
  { label: 'IRP', value: 'IRP' },
  { label: 'Construction', value: 'Construction' },
  { label: 'Safety', value: 'Safety' },
  { label: 'Disaster Prevention', value: 'Disaster Prevention' },
  { label: 'Enviroment', value: 'Enviroment' },
  { label: 'Health', value: 'Health' }
]

const getPartsByGroup = (groupName) => {
  if (!groupName) return defaultParts
  const key = String(groupName).trim()
  if (partMapping[key]) return partMapping[key]
  if (partMapping[`${key} Group`]) return partMapping[`${key} Group`]
  const withoutGroup = key.replace(/ Group$/i, '')
  if (partMapping[withoutGroup]) return partMapping[withoutGroup]
  return defaultParts
}

const onGroupChange = (row) => {
  if (!row) return
  const validParts = getPartsByGroup(row.GROUP_NAME).map(p => p.value)
  // Nếu Part hiện tại không nằm trong danh sách của Group mới -> Tự động reset
  if (row.PART_NAME && !validParts.includes(row.PART_NAME)) {
    row.PART_NAME = ''
  }
}

// Bảng dữ liệu & Phân trang
const tableRef = ref(null)
const tableData = ref([])
const selectedRows = ref([])
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const isSaving = ref(false)
const isLoading = ref(false)

// State cho Dialog Chi tiết đối soát & Rerun
const showDetailDialog = ref(false)
const detailLoading = ref(false)
const currentTask = ref(null)
const currentDetail = ref(null)
const activeDetailTab = ref('errors')
const activeCollapseDrawings = ref(['0'])
const detailReviewNote = ref('')
const isRerunning = ref(false)

// Biến Smart Polling (Thăm dò thông minh tự động bật/tắt)
let smartPollTimer = null
let smartPollCount = 0
const MAX_POLL_COUNT = 200 // Tối đa 10 phút (200 * 3s)

const stopSmartPolling = () => {
  if (smartPollTimer) {
    clearInterval(smartPollTimer)
    smartPollTimer = null
    smartPollCount = 0
  }
}

const startSmartPolling = () => {
  if (smartPollTimer) return
  smartPollCount = 0
  smartPollTimer = setInterval(async () => {
    smartPollCount++
    if (smartPollCount > MAX_POLL_COUNT) {
      stopSmartPolling()
      return
    }
    await fetchDataPage()
    const hasRunning = tableData.value.some(r => r.STATUS === 'RUNNING')
    if (!hasRunning) {
      stopSmartPolling()
    }
  }, 3000)
}

// 5 Chỉ số KPI toàn cục cố định
const kpiStats = ref({
  total: 0,
  ok: 0,
  err: 0,
  running: 0,
  waiting: 0
})

const fetchKpiStats = async () => {
  try {
    const res = await get_kpi_summary(selectedMonth.value || 'ALL', searchKeyword.value || 'ALL')
    if (res && res.length > 0) {
      kpiStats.value = {
        total: Number(res[0].TOTAL || 0),
        ok: Number(res[0].OK_COUNT || 0),
        err: Number(res[0].ERR_COUNT || 0),
        running: Number(res[0].RUNNING_COUNT || 0),
        waiting: Number(res[0].WAITING_COUNT || 0)
      }
    }
  } catch (e) {
    try {
      const resp = await axios.get(`${FASTAPI_BASE_URL}/mep_payment/kpi_summary`, {
        params: {
          payment_month: selectedMonth.value || 'ALL',
          keyword: searchKeyword.value || 'ALL'
        }
      })
      if (resp.data?.status === 'ok') {
        kpiStats.value = resp.data.data
      }
    } catch (apiErr) { }
  }
}

// Tải dữ liệu bảng phân trang
const fetchDataPage = async () => {
  isLoading.value = true
  try {
    const statusParam = activeKpiFilter.value !== 'ALL'
      ? activeKpiFilter.value
      : (selectedStatus.value || 'ALL')

    const [rows, totalCount] = await Promise.all([
      get_data_page(page.value, pageSize.value, statusParam, selectedMonth.value || 'ALL', searchKeyword.value || 'ALL'),
      get_total_row(statusParam, selectedMonth.value || 'ALL', searchKeyword.value || 'ALL')
    ])

    tableData.value = (rows || []).map(r => ({ ...r, isNew: false, isEditing: false }))
    total.value = (totalCount && totalCount[0]?.TOTAL) ? Number(totalCount[0].TOTAL) : tableData.value.length

    // Kiểm tra xem có task nào đang chạy không để kích hoạt Smart Polling
    const hasRunning = tableData.value.some(r => r.STATUS === 'RUNNING')
    if (hasRunning) {
      startSmartPolling()
    }
  } catch (error) {
    ElMessage.error(`Lỗi tải dữ liệu bảng: ${error.message || error}`)
  } finally {
    isLoading.value = false
  }
}

// Click vào thẻ KPI để lọc
const handleKpiFilter = (filterType) => {
  activeKpiFilter.value = filterType
  selectedStatus.value = ''
  page.value = 1
  fetchDataPage()
}

// Bấm Reload
const handleReload = () => {
  fetchKpiStats()
  fetchDataPage()
}

// Thêm dòng mới (Insert)
const handleInsert = () => {
  const newRow = {
    STT: tableData.value.length + 1,
    KEYID: '',
    TASK_NAME: '',
    PAYMENT_MONTH: selectedMonth.value || new Date().toISOString().slice(0, 7),
    PIC: loginUserName.value || '',
    GROUP_NAME: '',
    PART_NAME: '',
    STATUS: 'WAITING',
    PROGRESS: 0,
    ERROR_COUNT: 0,
    RESULT_LINK: '',
    isNew: true,
    isEditing: true
  }
  tableData.value.push(newRow)
}

// Lưu dữ liệu (Save)
const handleSave = async () => {
  const rowsToSave = tableData.value.filter(r => r.isNew || r.isEditing)
  if (rowsToSave.length === 0) {
    ElMessage.info('Không có thay đổi nào cần lưu.')
    return
  }

  // Validate các trường bắt buộc
  for (const r of rowsToSave) {
    if (!r.KEYID || !String(r.KEYID).trim()) {
      ElMessage.warning('Vui lòng nhập Mã số công việc (WO) cho tất cả các dòng!')
      return
    }
  }

  isSaving.value = true
  try {
    await save_mep_rows(rowsToSave)
    ElMessage.success(`Đã lưu thành công ${rowsToSave.length} bản ghi!`)
    await handleReload()
  } catch (error) {
    ElMessage.error(`Lỗi khi lưu dữ liệu: ${error.response?.data?.detail || error.message || error}`)
  } finally {
    isSaving.value = false
  }
}

// Xóa dòng được chọn (Delete)
const handleDelete = () => {
  if (selectedRows.value.length === 0) {
    ElMessage.warning('Vui lòng chọn ít nhất 1 dòng để xóa.')
    return
  }

  ElMessageBox.confirm(
    `Bạn có chắc chắn muốn xóa ${selectedRows.value.length} dòng đã chọn không? (Toàn bộ dữ liệu trên MinIO và ổ cứng sẽ được dọn dẹp sạch sẽ)`,
    'Xác nhận xóa',
    { confirmButtonText: 'Xóa ngay', cancelButtonText: 'Hủy', type: 'warning' }
  ).then(async () => {
    const keyidsToDelete = selectedRows.value.map(r => r.KEYID).filter(Boolean)
    try {
      await delete_mep_rows(keyidsToDelete)
      ElMessage.success(`Đã xóa thành công ${keyidsToDelete.length} bản ghi!`)
      await handleReload()
    } catch (error) {
      ElMessage.error(`Lỗi khi xóa: ${error.response?.data?.detail || error.message || error}`)
    }
  }).catch(() => { })
}

// Chọn dòng Checkbox
const handleSelectionChange = (selection) => {
  selectedRows.value = selection
}

// Chuyển trang & Đổi kích thước trang
const handlePageChange = (newPage) => {
  page.value = newPage
  fetchDataPage()
}

const handleSizeChange = (newSize) => {
  pageSize.value = newSize
  page.value = 1
  fetchDataPage()
}

// Upload file Excel dự toán
const handleUploadExcel = async (file, row) => {
  if (!file || !row) return

  // Kiểm tra kích thước file
  const fileSizeMb = file.size / (1024 * 1024)
  if (fileSizeMb > MAX_UPLOAD_SIZE_MB) {
    ElMessage.error(`Dung lượng file (${fileSizeMb.toFixed(1)}MB) vượt quá giới hạn tối đa ${MAX_UPLOAD_SIZE_MB}MB!`)
    return
  }

  const formData = new FormData()
  formData.append('file', file.raw)
  formData.append('KEYID', row.KEYID)
  if (row.PAYMENT_MONTH) {
    formData.append('payment_month', row.PAYMENT_MONTH)
  }

  row.STATUS = 'RUNNING'
  row.PROGRESS = 5
  ElMessage.info(`Đang tải lên file và khởi chạy AI cho [${row.KEYID}]...`)

  try {
    const resp = await axios.post(`${FASTAPI_BASE_URL}/mep_payment/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    if (resp.data?.status === 'accepted') {
      ElMessage.success(`Đã tiếp nhận file của [${row.KEYID}], AI đang bóc tách ngầm!`)
      startSmartPolling()
    }
  } catch (error) {
    row.STATUS = 'CANCEL'
    ElMessage.error(`Lỗi tải lên file: ${error.response?.data?.detail || error.message || error}`)
  }
}

// Mở Modal xem chi tiết kết quả đối soát
const openDetailModal = async (row) => {
  currentTask.value = row
  detailReviewNote.value = row.REVIEW_NOTE || ''
  showDetailDialog.value = true
  detailLoading.value = true
  activeDetailTab.value = 'errors'
  currentDetail.value = null

  try {
    // Truyền trực tiếp tháng thanh toán để Backend đọc cache trong 0ms (không cần kết nối DB)
    const resp = await axios.get(`${FASTAPI_BASE_URL}/mep_payment/detail/${encodeURIComponent(row.KEYID)}`, {
      params: {
        status: row.STATUS,
        error_count: row.ERROR_COUNT,
        reason: row.REASON,
        month: row.PAYMENT_MONTH || ''
      }
    })
    currentDetail.value = resp.data
  } catch (error) {
    ElMessage.error(`Lỗi tải chi tiết: ${error.response?.data?.detail || error.message || error}`)
  } finally {
    detailLoading.value = false
  }
}

const handleCloseDetailDialog = () => {
  showDetailDialog.value = false
  currentDetail.value = null
  currentTask.value = null
}

// Gửi phê duyệt từ Modal (Lưu Knox ID vào Database)
const submitDetailReview = async (decision) => {
  if (!currentTask.value) return

  const reviewerKnoxId = loginKnoxId.value || 'Engineer'

  try {
    await axios.post(`${FASTAPI_BASE_URL}/mep_payment/review`, {
      keyid: currentTask.value.KEYID,
      decision: decision,
      note: detailReviewNote.value || '',
      reviewer: reviewerKnoxId
    })

    currentTask.value.REVIEW_DECISION = decision
    currentTask.value.REVIEW_NOTE = detailReviewNote.value
    currentTask.value.REVIEW_BY = reviewerKnoxId

    ElMessage.success(`Đã lưu quyết định: ${decision === 'APPROVED' ? 'Phê duyệt' : 'Từ chối'}`)
    handleReload()
  } catch (error) {
    ElMessage.error(`Lỗi lưu phê duyệt: ${error.response?.data?.detail || error.message || error}`)
  }
}

// Phê duyệt nhanh ngay trên bảng
const handleReview = async (row, decision) => {
  const reviewerKnoxId = loginKnoxId.value || 'Engineer'
  try {
    await axios.post(`${FASTAPI_BASE_URL}/mep_payment/review`, {
      keyid: row.KEYID,
      decision: decision,
      note: '',
      reviewer: reviewerKnoxId
    })
    row.REVIEW_DECISION = decision
    row.REVIEW_BY = reviewerKnoxId
    ElMessage.success(`Đã cập nhật quyết định cho [${row.KEYID}]`)
  } catch (error) {
    ElMessage.error(`Lỗi phê duyệt: ${error.response?.data?.detail || error.message || error}`)
  }
}

// Chạy lại AI (Rerun)
const handleRerun = async (task) => {
  if (!task || !task.KEYID) return
  isRerunning.value = true
  ElMessage.info(`Đang kích hoạt chạy lại AI cho [${task.KEYID}]...`)

  try {
    const resp = await axios.post(`${FASTAPI_BASE_URL}/mep_payment/rerun/${encodeURIComponent(task.KEYID)}`)
    if (resp.data?.status === 'ok') {
      ElMessage.success(`Đã bắt đầu chạy lại AI cho [${task.KEYID}]!`)
      task.STATUS = 'RUNNING'
      task.PROGRESS = 5
      startSmartPolling()
    }
  } catch (error) {
    ElMessage.error(`Lỗi rerun: ${error.response?.data?.detail || error.message || error}`)
  } finally {
    isRerunning.value = false
  }
}

// Tải file báo cáo (.zip / .xlsx)
const handleDownloadFile = (row) => {
  if (!row.RESULT_LINK) {
    ElMessage.warning('Chưa có file báo cáo kết quả.')
    return
  }
  const cleanLink = row.RESULT_LINK.replace(/^\//, '')
  const fullUrl = `${FASTAPI_BASE_URL}/${cleanLink}`
  window.open(fullUrl, '_blank')
}

// Xuất file CSV
const handleExportCsv = () => {
  if (tableData.value.length === 0) {
    ElMessage.info('Không có dữ liệu để xuất.')
    return
  }
  const headers = ['STT', 'SỐ CÔNG VIỆC', 'TÊN CÔNG VIỆC', 'THÁNG TT', 'PIC', 'GROUP', 'PART', 'TRẠNG THÁI', 'SỐ LỖI', 'QUYẾT ĐỊNH', 'NGƯỜI DUYỆT']
  const rows = tableData.value.map(r => [
    r.STT, `"${r.KEYID}"`, `"${r.TASK_NAME || ''}"`, r.PAYMENT_MONTH, `"${r.PIC || ''}"`,
    `"${r.GROUP_NAME || ''}"`, `"${r.PART_NAME || ''}"`, r.STATUS, r.ERROR_COUNT,
    r.REVIEW_DECISION || '', r.REVIEW_BY || ''
  ])
  const csvContent = '\uFEFF' + [headers.join(','), ...rows.map(e => e.join(','))].join('\n')
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.setAttribute('href', url)
  link.setAttribute('download', `MEP_Payment_${selectedMonth.value || 'ALL'}_${Date.now()}.csv`)
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

// URL ảnh phục vụ Lightbox & Thư viện ảnh
const getImgUrl = (relUrl) => {
  if (!relUrl) return ''
  if (relUrl.startsWith('http://') || relUrl.startsWith('https://')) return relUrl
  const clean = relUrl.replace(/^\//, '')
  const m = currentTask.value?.PAYMENT_MONTH || ''
  const query = m ? `?month=${encodeURIComponent(m)}` : ''
  return `${FASTAPI_BASE_URL}/${clean}${query}`
}

const previewImageList = computed(() => {
  if (!currentDetail.value?.images) return []
  return currentDetail.value.images.map(img => getImgUrl(img.url))
})

const errorTypeEntries = computed(() => {
  if (!currentDetail.value?.error_types) return []
  return Object.entries(currentDetail.value.error_types)
})

// Theo dõi thay đổi của Bộ lọc
watch([selectedStatus, selectedMonth], () => {
  activeKpiFilter.value = 'ALL'
  page.value = 1
  handleReload()
})

// Khởi chạy khi nạp Component
onMounted(() => {
  _userInfo.value = getUserInfo()
  fetchKpiStats()
  fetchDataPage()
})

onUnmounted(() => {
  stopSmartPolling()
})
</script>

<style scoped>
@import './operation.css';
</style>

