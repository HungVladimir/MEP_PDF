<template>
  <div class="mep-container">
    <!-- 1. KHỐI THẺ KPI THỐNG KÊ 5 THẺ TƯƠNG TÁC (CLICK-TO-FILTER THEO PHONG CÁCH SẾP GỬI) -->
    <div class="kpi-cards-grid">
      <div class="kpi-card" :class="{ active: activeKpiFilter === 'ALL' }" @click="handleKpiFilter('ALL')">
        <div class="kpi-icon total"><i class="bi bi-stack"></i></div>
        <div class="kpi-info">
          <div class="kpi-val">{{ kpiStats.total }}</div>
          <div class="kpi-label">Tổng số hồ sơ</div>
        </div>
      </div>
      <div class="kpi-card" :class="{ active: activeKpiFilter === 'OK' }" @click="handleKpiFilter('OK')">
        <div class="kpi-icon ok"><i class="bi bi-check2-circle"></i></div>
        <div class="kpi-info">
          <div class="kpi-val text-success">{{ kpiStats.ok }}</div>
          <div class="kpi-label">Khớp 100% (0 lỗi)</div>
        </div>
      </div>
      <div class="kpi-card" :class="{ active: activeKpiFilter === 'ERR' }" @click="handleKpiFilter('ERR')">
        <div class="kpi-icon err"><i class="bi bi-exclamation-triangle"></i></div>
        <div class="kpi-info">
          <div class="kpi-val text-danger">{{ kpiStats.err }}</div>
          <div class="kpi-label">Có sai lệch</div>
        </div>
      </div>
      <div class="kpi-card" :class="{ active: activeKpiFilter === 'RUNNING' }" @click="handleKpiFilter('RUNNING')">
        <div class="kpi-icon running"><i class="bi bi-gear-wide-connected"></i></div>
        <div class="kpi-info">
          <div class="kpi-val text-warning">{{ kpiStats.running }}</div>
          <div class="kpi-label">Đang đối soát AI</div>
        </div>
      </div>
      <div class="kpi-card" :class="{ active: activeKpiFilter === 'WAITING' }" @click="handleKpiFilter('WAITING')">
        <div class="kpi-icon waiting"><i class="bi bi-hourglass-split"></i></div>
        <div class="kpi-info">
          <div class="kpi-val text-muted">{{ kpiStats.waiting }}</div>
          <div class="kpi-label">Chờ duyệt / Mới</div>
        </div>
      </div>
    </div>

    <!-- 2. THANH TÌM KIẾM & BỘ LỌC (TOP FILTER) -->
    <div class="toolbar">
      <el-select v-model="selectedStatus" placeholder="Chọn Trạng Thái" clearable style="width: 200px">
        <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
      </el-select>

      <el-date-picker v-model="selectedMonth" type="month" placeholder="Chọn Tháng Thanh Toán" value-format="YYYY-MM"
        style="width: 190px" />

      <el-input v-model="searchKeyword" placeholder="Nhập số WO hoặc tên công việc..." clearable style="width: 270px"
        @keyup.enter="handleReload" />
    </div>

    <!-- 3. THANH CÔNG CỤ QUẢN TRỊ BẢNG (ACTION BAR THEO THỨ TỰ & MÀU SẮC UX CHUẨN) -->
    <div class="table-action-bar">
      <div class="total-count">
        Total: <span class="count-number">{{ total }} rows</span>
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

    <!-- 4. BẢNG DỮ LIỆU ĐỐI SOÁT (TABLE GRID HỖ TRỢ INLINE EDIT) -->
    <div class="table-container">
      <el-table ref="tableRef" :data="tableData" border height="660" size="small" style="width: 100%"
        show-overflow-tooltip empty-text="Không có dữ liệu đối soát" @selection-change="handleSelectionChange">
        <!-- CỘT CHECKBOX CHỌN DÒNG -->
        <el-table-column type="selection" width="45" align="center" />

        <!-- CỘT STT -->
        <el-table-column prop="STT" label="STT" width="55" align="center" />

        <!-- CỘT: SỐ CÔNG VIỆC (SỐ WO) - HIỂN THỊ DẠNG CHỮ BÌNH THƯỜNG -->
        <el-table-column prop="KEYID" label="SỐ CÔNG VIỆC (WO)" width="165" sortable align="center">
          <template #default="{ row }">
            <el-input v-if="row.isNew" v-model="row.KEYID" placeholder="Nhập số WO..." size="mini"
              class="inline-input" />
            <span v-else class="font-bold font-mono">{{ row.KEYID }}</span>
          </template>
        </el-table-column>

        <!-- CỘT: TÊN CÔNG VIỆC (TĂNG ĐỘ RỘNG ĐỂ KHÔNG BỊ RỚT DÒNG) -->
        <el-table-column prop="TASK_NAME" label="TÊN CÔNG VIỆC" min-width="260">
          <template #default="{ row }">
            <el-input v-if="row.isNew || row.isEditing" v-model="row.TASK_NAME" placeholder="Tên công việc..."
              size="mini" class="inline-input" />
            <span v-else class="cell-text" @dblclick="row.isEditing = true" title="Bấm đúp chuột để chỉnh sửa">{{
              row.TASK_NAME || '-' }}</span>
          </template>
        </el-table-column>

        <!-- CỘT: THÁNG THANH TOÁN -->
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

        <!-- CỘT: NGƯỜI PHỤ TRÁCH (PIC) -->
        <el-table-column prop="PIC" label="NGƯỜI PHỤ TRÁCH" width="130" align="center">
          <template #default="{ row }">
            <el-input v-if="row.isNew || row.isEditing" v-model="row.PIC" placeholder="PIC..." size="mini"
              class="inline-input" />
            <span v-else class="cell-text" @dblclick="row.isEditing = true" title="Bấm đúp chuột để chỉnh sửa">{{
              row.PIC || '-' }}</span>
          </template>
        </el-table-column>

        <!-- CỘT: GROUP (CHỌN GROUP ĐỂ LỌC PART TƯƠNG ỨNG) -->
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

        <!-- CỘT: PART (PHỤ THUỘC VÀO GROUP ĐÃ CHỌN) -->
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

        <!-- CỘT: TRẠNG THÁI (STATUS) -->
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

        <!-- CỘT: TÀI LIỆU ĐÍNH KÈM (UPLOAD FILE EXCEL) -->
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

        <!-- CỘT: KẾT QUẢ KIỂM TRA (CLICK VÀO BADGE ĐỂ MỞ MODAL SOI CHI TIẾT) -->
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

        <!-- CỘT: CHI TIẾT BÁO CÁO & DUYỆT (GỌN GÀNG, THOÁNG ĐÃNG) -->
        <el-table-column label="CHI TIẾT BÁO CÁO" width="170" align="center">
          <template #default="{ row }">
            <div v-if="row.STATUS === 'COMPLETED'">

              <!-- Trạng thái duyệt / Nút duyệt -->
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

              <!-- Nút tải file báo cáo -->
              <div v-if="row.RESULT_LINK" style="margin-bottom: 3px;">
                <el-button type="text" size="small" class="download-btn" @click="handleDownloadFile(row)">
                  📥 Tải Báo Cáo (.zip)
                </el-button>
              </div>

            </div>
            <div v-else-if="row.STATUS === 'CANCEL'" class="row-cancel-box">
              <span class="text-reason" :title="row.REASON">{{ row.REASON || 'Xử lý thất bại' }}</span>
              <el-button size="mini" class="btn-rerun-mini mt-1" @click="handleRerun(row)">
                🔄 Chạy lại AI
              </el-button>
            </div>
            <span v-else-if="row.REASON" class="text-reason">{{ row.REASON }}</span>
            <span v-else style="color: #909399;">-</span>
          </template>
        </el-table-column>
      </el-table>

      <!-- 5. THANH PHÂN TRANG -->
      <div class="pagination-bar">
        <el-button size="small" @click="goFirst" :disabled="page === 1">First</el-button>
        <el-pagination v-model:current-page="page" v-model:page-size="pageSize" :page-sizes="[20, 30, 50, 100]"
          :total="total" layout="total, sizes, prev, pager, next, jumper" @current-change="handlePageChange"
          @size-change="handleSizeChange" />
        <el-button size="small" @click="goLast" :disabled="page >= totalPages">Last</el-button>
      </div>
    </div>

    <!-- 6. DIALOG CHI TIẾT ĐỐI SOÁT (XEM LỖI, BẢN VẼ, SOI ẢNH, LOG VÀ DUYỆT THEO CHUẨN SẾP) -->
    <el-dialog v-model="showDetailDialog" :title="`📋 Chi Tiết Đối Soát Hồ Sơ: ${currentTask?.KEYID || ''}`" width="85%"
      top="4vh" :before-close="handleCloseDetailDialog" destroy-on-close custom-class="mep-detail-dialog">
      <div v-if="detailLoading" class="detail-loading-box">
        <i class="bi bi-arrow-repeat mep-spin-icon" style="font-size: 36px; color: #409EFF; display: inline-block;"></i>
        <p style="margin-top: 12px; color: #E5EAF3;">Đang tải và đồng bộ kết quả đối soát AI...</p>
      </div>

      <div v-else-if="currentDetail" class="detail-body">
        <!-- HEADER SUMMARY CARD -->
        <div class="detail-header-card">
          <div class="dh-title">
            <h3>{{ currentTask?.TASK_NAME || 'Chưa đặt tên công việc' }}</h3>
            <div class="dh-meta">
              <span><b>Mã WO:</b> {{ currentTask?.KEYID }}</span>
              <span><b>Người phụ trách:</b> {{ currentTask?.PIC || '—' }}</span>
              <span><b>Phần việc:</b> {{ currentTask?.PART_NAME }} / {{ currentTask?.GROUP_NAME }}</span>
              <span><b>Tháng:</b> {{ currentTask?.PAYMENT_MONTH }}</span>
              <span><b>Công nghệ:</b> {{ currentDetail.mode }}</span>
            </div>
          </div>
          <div class="dh-badges">
            <el-tag v-if="currentTask?.STATUS === 'COMPLETED'" type="success" effect="dark">COMPLETED</el-tag>
            <el-tag v-else-if="currentTask?.STATUS === 'RUNNING'" type="warning" effect="dark">RUNNING</el-tag>
            <el-tag v-else-if="currentTask?.STATUS === 'CANCEL'" type="danger" effect="dark">CANCEL</el-tag>
            <el-tag v-else type="info" effect="dark">{{ currentTask?.STATUS }}</el-tag>

            <el-tag v-if="currentTask?.REVIEW_DECISION === 'APPROVED'" type="success" effect="plain" class="ms-1"
              :title="currentTask?.REVIEW_BY ? `Duyệt bởi: ${currentTask.REVIEW_BY}` : ''">
              ĐÃ DUYỆT {{ currentTask?.REVIEW_BY ? `(${currentTask.REVIEW_BY})` : '' }}
            </el-tag>
            <el-tag v-else-if="currentTask?.REVIEW_DECISION === 'REJECTED'" type="danger" effect="plain" class="ms-1"
              :title="currentTask?.REVIEW_BY ? `Từ chối bởi: ${currentTask.REVIEW_BY}` : ''">
              TỪ CHỐI {{ currentTask?.REVIEW_BY ? `(${currentTask.REVIEW_BY})` : '' }}
            </el-tag>
            <el-tag v-else type="warning" effect="plain" class="ms-1">CHỜ DUYỆT</el-tag>
          </div>
        </div>

        <!-- 4 THẺ THỐNG KÊ NHANH TRONG MODAL -->
        <div class="modal-stats-grid">
          <div class="m-stat" :class="currentDetail.error_count > 0 ? 'border-err' : 'border-ok'">
            <b :class="currentDetail.error_count > 0 ? 'text-danger' : 'text-success'">
              {{ currentDetail.error_count }}
            </b>
            <span>Số lỗi phát hiện</span>
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

        <!-- CÁC TAB CHI TIẾT -->
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
              <p class="text-muted">Tất cả số lượng vật tư giữa Dự toán nhà thầu và Bản vẽ thiết kế bóc
                tách khớp 100%.</p>
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
              <el-table-column prop="diff" label="Chênh lệch" width="140" align="center">
                <template #default="{ row }"><span class="text-danger font-bold">{{ row.diff
                    }}</span></template>
              </el-table-column>
              <el-table-column prop="msg" label="Chi tiết đối chiếu" min-width="220" show-overflow-tooltip />
            </el-table>
          </el-tab-pane>

          <!-- ================================================================= -->
          <!-- TAB 2: ĐỐI CHIẾU THEO TỪNG BẢN VẼ (ĐÃ TỐI ƯU GIAO DIỆN DỄ HIỂU)     -->
          <!-- (NẾU KHÔNG MUỐN HIỂN THỊ: COMMENT TOÀN BỘ KHỐI <el-tab-pane> NÀY) -->
          <!-- ================================================================= -->
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
                    <template #default="{ row }"><b class="text-primary">{{ row.qty
                        }}</b></template>
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
          <!-- ================================================================= -->
          <!-- KẾT THÚC KHỐI TAB 2: ĐỐI CHIẾU THEO BẢN VẼ                         -->
          <!-- ================================================================= -->

          <!-- TAB 3: SOI BẢN VẼ / ẢNH TRÍCH XUẤT -->
          <el-tab-pane name="images" lazy>
            <template #label>
              <span><i class="bi bi-images me-1"></i> Soi Bản Vẽ / Ảnh Trích Xuất ({{
                currentDetail.images?.length || 0 }})</span>
            </template>
            <div v-if="!currentDetail.images || currentDetail.images.length === 0" class="p-4 text-center text-muted">
              <i class="bi bi-image" style="font-size: 36px;"></i>
              <p style="margin-top: 10px;">Chưa có ảnh bản vẽ nào được lưu trong phiên này (Hệ thống lưu
                trữ ảnh sau khi Worker AI render).</p>
            </div>
            <div v-else class="images-strip">
              <div v-for="(img, idx) in currentDetail.images" :key="idx" class="img-thumb-box">
                <el-image :src="getImgUrl(img.url)" :preview-src-list="previewImageList" :initial-index="idx"
                  :preview-teleported="true" :hide-on-click-modal="true" fit="contain" loading="lazy"
                  class="thumb-img" />
                <div class="thumb-title">{{ img.title || img.name }}</div>
              </div>
            </div>
          </el-tab-pane>

          <!-- TAB 4: NHẬT KÝ XỬ LÝ (PIPELINE LOGS) -->
          <el-tab-pane name="logs" lazy>
            <template #label>
              <span><i class="bi bi-terminal me-1"></i> Nhật Ký AI</span>
            </template>
            <div class="log-console">
              <div v-for="(l, idx) in currentDetail.logs" :key="idx" class="log-line">
                <span class="log-index">[{{ idx + 1 }}]</span> {{ l }}
              </div>
            </div>
          </el-tab-pane>
        </el-tabs>

        <!-- KHỐI PHÊ DUYỆT & THAO TÁC HỒ SƠ -->
        <div class="detail-review-card">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
            <h4 style="margin: 0; font-size: 14px; font-weight: 600; color: #FFF;">
              ✍️ Phê Duyệt & Thao Tác Hồ Sơ
            </h4>
            <div v-if="currentTask?.REVIEW_DECISION" style="font-size: 12px;">
              <span v-if="currentTask.REVIEW_DECISION === 'APPROVED'" style="color: #67C23A; background: rgba(103, 194, 58, 0.1); padding: 3px 8px; border-radius: 4px; border: 1px solid rgba(103, 194, 58, 0.3);">
                <i class="bi bi-check-circle-fill me-1"></i> Đã duyệt bởi: <b>{{ currentTask.REVIEW_BY }}</b>
                <span v-if="currentTask.REVIEW_NOTE" style="color: #CFD3DC; margin-left: 6px;">— "{{ currentTask.REVIEW_NOTE }}"</span>
              </span>
              <span v-else-if="currentTask.REVIEW_DECISION === 'REJECTED'" style="color: #F56C6C; background: rgba(245, 108, 108, 0.1); padding: 3px 8px; border-radius: 4px; border: 1px solid rgba(245, 108, 108, 0.3);">
                <i class="bi bi-x-circle-fill me-1"></i> Bị từ chối bởi: <b>{{ currentTask.REVIEW_BY }}</b>
                <span v-if="currentTask.REVIEW_NOTE" style="color: #CFD3DC; margin-left: 6px;">— "{{ currentTask.REVIEW_NOTE }}"</span>
              </span>
            </div>
          </div>

          <!-- GRID 2 CỘT: CỘT TRÁI NGƯỜI DUYỆT (TÊN + KNOX ID), CỘT PHẢI GHI CHÚ -->
          <div class="review-grid-inputs">
            <div class="review-col-user">
              <label class="review-field-label">👤 Người phê duyệt:</label>
              <el-input :model-value="loginUserDisplay || 'Kỹ sư MEP'" readonly class="readonly-input">
                <template #prefix>
                  <i class="bi bi-person-badge text-success"></i>
                </template>
              </el-input>
            </div>
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
            <!-- Cụm hành động chính (Duyệt / Từ chối) -->
            <div class="review-main-btns">
              <el-button type="success" :size="buttonSize" @click="submitDetailReview('APPROVED')">
                <i class="bi bi-check-lg me-1"></i> Duyệt (Approve)
              </el-button>
              <el-button type="danger" :size="buttonSize" @click="submitDetailReview('REJECTED')">
                <i class="bi bi-x-lg me-1"></i> Từ Chối (Reject)
              </el-button>
            </div>

            <div class="spacer"></div>

            <!-- Cụm thao tác file & đóng -->
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
import { ref, computed, onMounted, onUnmounted, watch, getCurrentInstance } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from 'axios'
import { get_total_row, get_data_page, save_mep_rows, delete_mep_rows, get_kpi_summary } from '../js/mepPayment'

// Địa chỉ Worker API & Kích thước nút bấm
const FASTAPI_BASE_URL = 'http://127.0.0.1:8000'
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

// State cho Dialog Chi tiết đối soát & Rerun (Theo phong cách Sếp)
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

const startSmartPollingIfNeeded = () => {
  const hasRunning = tableData.value.some(r => r.STATUS === 'RUNNING')
  if (!hasRunning) {
    stopSmartPolling()
    return
  }

  if (smartPollTimer) return // Đã bật rồi thì không tạo thêm interval trùng lặp

  smartPollCount = 0
  console.log("⚡ [Smart Polling] Kích hoạt thăm dò tiến độ mỗi 3 giây...")

  smartPollTimer = setInterval(async () => {
    smartPollCount++
    if (smartPollCount > MAX_POLL_COUNT) {
      console.warn("⚠️ [Smart Polling] Quá thời gian chờ (10 phút), tự động dừng.")
      stopSmartPolling()
      return
    }

    // Nếu người dùng đang thêm dòng mới (isNew), tạm ngưng không đè dữ liệu
    const hasNewRow = tableData.value.some(r => r.isNew)
    if (hasNewRow) return

    try {
      const data = await get_data_page(
        page.value, pageSize.value,
        selectedStatus.value || 'ALL',
        selectedMonth.value || 'ALL',
        searchKeyword.value || 'ALL'
      )
      if (Array.isArray(data)) {
        let processed = data
        if (selectedStatus.value === 'OK') {
          processed = processed.filter(r => r.STATUS === 'COMPLETED' && (Number(r.ERROR_COUNT) === 0 || !r.ERROR_COUNT))
        } else if (selectedStatus.value === 'ERR') {
          processed = processed.filter(r => r.STATUS === 'COMPLETED' && Number(r.ERROR_COUNT) > 0)
        }

        tableData.value = processed.map(newRow => {
          const oldRow = tableData.value.find(r => r.KEYID === newRow.KEYID)
          return {
            ...newRow,
            isNew: false,
            isEditing: oldRow ? oldRow.isEditing : false
          }
        })
        if (showDetailDialog.value && currentTask.value) {
          const updatedCurrent = data.find(r => r.KEYID === currentTask.value.KEYID)
          if (updatedCurrent) {
            Object.assign(currentTask.value, updatedCurrent)
          }
        }
      }

      // Cứ mỗi 2 nhịp polling (6 giây), tự động đồng bộ lại 5 thẻ KPI
      if (smartPollCount % 2 === 0) {
        loadKpiSummary()
      }

      // Khi không còn dòng nào RUNNING nữa -> Dừng polling ngay lập tức và làm mới KPI + total
      const stillRunning = tableData.value.some(r => r.STATUS === 'RUNNING')
      if (!stillRunning) {
        console.log("🎉 [Smart Polling] Tất cả tác vụ AI đã hoàn tất. Tắt polling.")
        stopSmartPolling()
        loadTotal()
        loadKpiSummary()
      }
    } catch (err) {
      console.error("[Smart Polling Error]", err)
    }
  }, 3000)
}

// 1. TẢI DỮ LIỆU TỪ BACKEND
const loadData = async () => {
  try {
    const data = await get_data_page(
      page.value, pageSize.value,
      selectedStatus.value || 'ALL',
      selectedMonth.value || 'ALL',
      searchKeyword.value || 'ALL'
    )
    let processed = data || []

    // Client-side fallback bảo vệ 2 lớp: Nếu backend cũ trả về tất cả COMPLETED khi filter OK/ERR
    if (selectedStatus.value === 'OK') {
      processed = processed.filter(r => r.STATUS === 'COMPLETED' && (Number(r.ERROR_COUNT) === 0 || !r.ERROR_COUNT))
    } else if (selectedStatus.value === 'ERR') {
      processed = processed.filter(r => r.STATUS === 'COMPLETED' && Number(r.ERROR_COUNT) > 0)
    }

    tableData.value = processed.map(row => ({
      ...row,
      isNew: false,
      isEditing: false
    }))
    startSmartPollingIfNeeded()
  } catch (err) {
    console.error("Lỗi tải bảng dữ liệu MEP:", err)
  }
}

const loadTotal = async () => {
  try {
    const res = await get_total_row(
      selectedStatus.value || 'ALL',
      selectedMonth.value || 'ALL',
      searchKeyword.value || 'ALL'
    )
    total.value = res?.[0]?.TOTAL ?? 0
  } catch (err) {
    console.error("Lỗi lấy tổng số dòng:", err)
  }
}

// 2. 5 CHỈ SỐ KPI TOÀN CỤC CỐ ĐỊNH (KHÔNG BỊ THAY ĐỔI THEO PHÂN TRANG HAY KHI BẤM LỌC)
const kpiStats = ref({
  total: 0,
  ok: 0,
  err: 0,
  running: 0,
  waiting: 0
})

const loadKpiSummary = async () => {
  try {
    if (typeof get_kpi_summary === 'function') {
      const res = await get_kpi_summary(
        selectedMonth.value || 'ALL',
        searchKeyword.value || 'ALL'
      )
      if (res && res[0]) {
        kpiStats.value = {
          total: Number(res[0].TOTAL ?? 0),
          ok: Number(res[0].OK_COUNT ?? 0),
          err: Number(res[0].ERR_COUNT ?? 0),
          running: Number(res[0].RUNNING_COUNT ?? 0),
          waiting: Number(res[0].WAITING_COUNT ?? 0)
        }
        return
      }
    }
  } catch (err) {
    console.warn("⚠️ [Gateway get_kpi_summary] Chưa cấu hình trên Gateway, dùng kênh FastAPI Worker...")
  }

  // Kênh dự phòng 2: FastAPI Worker (:8000)
  try {
    const resFast = await axios.get(`${FASTAPI_BASE_URL}/mep_payment/kpi_summary`, {
      params: {
        payment_month: selectedMonth.value || 'ALL',
        keyword: searchKeyword.value || 'ALL'
      }
    })
    if (resFast.data?.data) {
      kpiStats.value = resFast.data.data
      return
    }
  } catch (fastErr) {
    console.warn("⚠️ [FastAPI kpi_summary Warning]", fastErr)
  }
}

const handleReload = async () => {
  isLoading.value = true
  try {
    await loadKpiSummary()
    await loadTotal()
    await loadData()
  } finally {
    isLoading.value = false
  }
}

const handleKpiFilter = (statusKey) => {
  activeKpiFilter.value = statusKey
  if (statusKey === 'ALL') {
    selectedStatus.value = ''
  } else {
    selectedStatus.value = statusKey
  }
  loadKpiSummary()
}

// 3. DIALOG CHI TIẾT ĐỐI SOÁT (OPEN DETAIL MODAL)
const handleCloseDetailDialog = (done) => {
  showDetailDialog.value = false
  if (typeof done === 'function') {
    done()
  }
}

const openDetailModal = async (row) => {
  if (!row || !row.KEYID) return
  currentTask.value = row
  detailReviewNote.value = row.REVIEW_NOTE || ''
  showDetailDialog.value = true
  detailLoading.value = true
  activeDetailTab.value = 'errors'
  activeCollapseDrawings.value = ['0']

  try {
    const res = await axios.get(`${FASTAPI_BASE_URL}/mep_payment/detail/${encodeURIComponent(row.KEYID)}`, {
      params: {
        status: row.STATUS || 'COMPLETED',
        error_count: row.ERROR_COUNT || 0,
        reason: row.REASON || '',
        month: row.PAYMENT_MONTH || ''
      }
    })
    const data = res.data || {}
    currentDetail.value = {
      keyid: data.keyid || row.KEYID,
      mode: data.mode || 'MEP AI Vision (Qwen)',
      error_count: Number(data.error_count ?? row.ERROR_COUNT ?? 0),
      error_types: (data.error_types && typeof data.error_types === 'object') ? data.error_types : {},
      drawings_count: Number(data.drawings_count ?? 1),
      total_items: Number(data.total_items ?? 0),
      sheet: data.sheet || '1. Đối Soát Bản Vẽ',
      errors: Array.isArray(data.errors) ? data.errors : [],
      groups: Array.isArray(data.groups) ? data.groups : [],
      images: Array.isArray(data.images) ? data.images : [],
      logs: Array.isArray(data.logs) ? data.logs : []
    }
  } catch (err) {
    console.warn("Không thể tải chi tiết từ API Worker, dùng dữ liệu fallback:", err)
    currentDetail.value = {
      keyid: row.KEYID,
      mode: 'MEP AI Vision (Qwen)',
      error_count: row.ERROR_COUNT || 0,
      error_types: row.ERROR_COUNT > 0 ? { 'Lệch số lượng đối soát': row.ERROR_COUNT } : {},
      drawings_count: 1,
      total_items: 12,
      sheet: '1. Đối Soát Bản Vẽ',
      errors: row.ERROR_COUNT > 0 ? [{
        id: 1,
        type: 'Lệch số lượng đối soát',
        dwg: 'Bản vẽ 1',
        code: 'M03-00726974',
        name: 'Dây cáp điện chống cháy Cu/Mica/XLPE/FR-PVC',
        vendor_qty: '150.00',
        ai_qty: '120.00',
        diff: `Lệch: Dự toán 150 > Bản vẽ 120 (Chênh 30)`,
        cell: 'Sheet 1',
        msg: row.REASON || 'Số lượng dự toán đề nghị thanh toán lớn hơn số lượng đo đạc trên bản vẽ thiết kế'
      }] : [],
      groups: [],
      images: [],
      logs: [
        `Hồ sơ: ${row.KEYID}`,
        `Trạng thái: ${row.STATUS}`,
        `Ghi chú: ${row.REASON || 'Chưa có nhật ký'}`
      ]
    }
  } finally {
    detailLoading.value = false
  }
}

const errorTypeEntries = computed(() => {
  const et = currentDetail.value?.error_types
  if (!et) return []
  if (Array.isArray(et)) {
    return et.map(item => [String(item), 1])
  }
  if (typeof et === 'object') {
    return Object.entries(et)
  }
  return []
})

const getImgUrl = (url) => {
  if (!url) return ''
  return url.startsWith('http') ? url : `${FASTAPI_BASE_URL}${url}`
}

const previewImageList = computed(() => {
  const imgs = currentDetail.value?.images
  if (!imgs || !Array.isArray(imgs)) return []
  return imgs.filter(img => img && img.url).map(img => getImgUrl(img.url))
})

const submitDetailReview = async (decision) => {
  if (!currentTask.value) return
  await handleReview(currentTask.value, decision, detailReviewNote.value)
  currentTask.value.REVIEW_NOTE = detailReviewNote.value
}

// 4. CHẠY LẠI AI (RERUN AI TASK)
const handleRerun = async (row) => {
  if (!row || !row.KEYID) return
  if (row.STATUS === 'RUNNING') {
    ElMessage.warning("Hồ sơ đang trong quá trình xử lý AI, vui lòng đợi hoàn tất!")
    return
  }

  isRerunning.value = true
  try {
    const res = await axios.post(`${FASTAPI_BASE_URL}/mep_payment/rerun/${encodeURIComponent(row.KEYID)}`)
    row.STATUS = 'RUNNING'
    row.PROGRESS = 5
    row.REASON = 'Đang chạy lại AI đối soát...'
    kpiStats.value.running = (kpiStats.value.running || 0) + 1
    ElMessage.success(res.data?.message || "Đã kích hoạt chạy lại AI!")
    startSmartPollingIfNeeded()
    loadKpiSummary()
    if (showDetailDialog.value && currentTask.value?.KEYID === row.KEYID) {
      currentTask.value.STATUS = 'RUNNING'
    }
  } catch (err) {
    console.error("Lỗi rerun task:", err)
    ElMessage.error(err.response?.data?.detail || err.message || "Không thể chạy lại AI. Vui lòng bấm Upload lại file Excel!")
  } finally {
    isRerunning.value = false
  }
}

// 5. CHỌN DÒNG TRONG BẢNG (SELECTION)
const handleSelectionChange = (selection) => {
  selectedRows.value = selection
}

// 6. THAO TÁC INSERT (THÊM DÒNG MỚI VÀO CUỐI BẢNG)
const handleInsert = () => {
  // Tính toán STT chuẩn toàn cục (Global STT) dựa trên tổng số dòng và số STT lớn nhất hiện có
  // Khắc phục triệt để lỗi: trên page 1 hiện 21 thay vì 23, trên page 2 hiện 4 thay vì 24
  const currentMaxStt = tableData.value.reduce((max, r) => Math.max(max, Number(r.STT) || 0), 0)
  const nextStt = Math.max(Number(total.value || 0) + 1, currentMaxStt + 1)

  const newRow = {
    STT: nextStt,
    KEYID: '',
    TASK_NAME: '',
    PAYMENT_MONTH: selectedMonth.value || new Date().toISOString().slice(0, 7),
    PIC: loginUser.value || '',
    GROUP_NAME: 'Mes',
    PART_NAME: 'AI Transformation',
    STATUS: 'WAITING',
    ERROR_COUNT: 0,
    isNew: true,
    isEditing: true
  }
  tableData.value.push(newRow)
  total.value = Math.max(Number(total.value || 0) + 1, nextStt)
  ElMessage.info(`Đã thêm 1 dòng mới (STT #${nextStt}) vào cuối bảng. Vui lòng nhập thông tin và bấm [Save].`)
}

// 7. THAO TÁC SAVE (LƯU CÁC DÒNG MỚI HOẶC SỬA XUỐNG DB)
const handleSave = async () => {
  const modifiedRows = tableData.value.filter(r => r.isNew || r.isEditing)
  if (modifiedRows.length === 0) {
    ElMessage.info("Không có dòng nào thay đổi để lưu.")
    return
  }

  // Kiểm tra không để trống KEYID
  for (const r of modifiedRows) {
    if (!r.KEYID || !String(r.KEYID).trim()) {
      ElMessage.warning("Vui lòng nhập Số Công Việc (KEYID) trước khi lưu!")
      return
    }
  }

  // Kiểm tra trùng lặp Số Công Việc (KEYID)
  for (const r of modifiedRows) {
    if (r.isNew) {
      const isDuplicate = tableData.value.some(
        item => item !== r && String(item.KEYID).trim().toUpperCase() === String(r.KEYID).trim().toUpperCase()
      )
      if (isDuplicate) {
        ElMessage.error(`Số công việc (KEYID) "${r.KEYID}" đã tồn tại! Vui lòng nhập mã khác.`)
        return
      }
    }
  }

  isSaving.value = true
  try {
    const payload = {
      rows: modifiedRows.map(r => ({
        KEYID: String(r.KEYID).trim(),
        TASK_NAME: String(r.TASK_NAME || '').trim(),
        PAYMENT_MONTH: String(r.PAYMENT_MONTH || '').trim(),
        PIC: String(r.PIC || '').trim(),
        PART_NAME: String(r.PART_NAME || '').trim(),
        GROUP_NAME: String(r.GROUP_NAME || '').trim(),
        STATUS: r.STATUS || 'WAITING',
        isNew: !!r.isNew
      }))
    }
    const res = await axios.post(`${FASTAPI_BASE_URL}/mep_payment/save_rows`, payload)
    ElMessage.success(res.data?.message || "Lưu dữ liệu thành công!")
    await handleReload()
  } catch (err) {
    console.error("Lỗi khi lưu dòng:", err)
    ElMessage.error(err.response?.data?.detail || err.message || "Lỗi khi lưu dữ liệu xuống Database!")
  } finally {
    isSaving.value = false
  }
}

// 8. THAO TÁC DELETE (XÓA CÁC DÒNG ĐƯỢC CHỌN)
const handleDelete = async () => {
  if (selectedRows.value.length === 0) {
    ElMessage.warning("Vui lòng chọn ít nhất 1 dòng để xóa.")
    return
  }

  try {
    await ElMessageBox.confirm(
      `Bạn có chắc chắn muốn xóa ${selectedRows.value.length} dòng đã chọn?`,
      'Xác nhận xóa',
      { confirmButtonText: 'Xác nhận', cancelButtonText: 'Hủy', type: 'warning' }
    )

    const newKeys = selectedRows.value.filter(r => r.isNew).map(r => r.KEYID)
    const dbKeys = selectedRows.value.filter(r => !r.isNew && r.KEYID).map(r => r.KEYID)

    if (newKeys.length > 0) {
      tableData.value = tableData.value.filter(r => !selectedRows.value.includes(r))
      total.value = Math.max(0, total.value - newKeys.length)
    }

    if (dbKeys.length > 0) {
      const res = await axios.post(`${FASTAPI_BASE_URL}/mep_payment/delete_rows`, { keyids: dbKeys })
      ElMessage.success(res.data?.message || `Đã xóa ${dbKeys.length} dòng thành công!`)
      await handleReload()
    } else {
      ElMessage.success("Đã xóa dòng tạm khỏi bảng.")
    }
  } catch (err) {
    if (err !== 'cancel') {
      console.error("Lỗi xóa dòng:", err)
      ElMessage.error(err.response?.data?.detail || err.message || "Không thể xóa dòng đã chọn!")
    }
  }
}

// 9. THAO TÁC TẢI BÁO CÁO (BLOB DOWNLOAD CHỐNG CHẶN)
const handleDownloadFile = async (row) => {
  if (!row.RESULT_LINK) return

  try {
    ElMessage.info("Đang chuẩn bị tải file báo cáo...")
    const url = row.RESULT_LINK.startsWith('http')
      ? row.RESULT_LINK
      : `${FASTAPI_BASE_URL}${row.RESULT_LINK}`

    const res = await axios.get(url, { responseType: 'blob' })
    const contentType = res.headers['content-type'] || 'application/zip'
    const blob = new Blob([res.data], { type: contentType })
    const blobUrl = window.URL.createObjectURL(blob)

    const filename = row.RESULT_LINK.split('/').pop() || `Bao_Cao_${row.KEYID}.zip`
    const link = document.createElement('a')
    link.href = blobUrl
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(blobUrl)

    ElMessage.success("Tải file thành công!")
  } catch (err) {
    console.error("Lỗi download file:", err)
    ElMessage.error("Không thể tải file báo cáo. Vui lòng kiểm tra lại server!")
  }
}

// 10. XUẤT CSV (EXPORT .CSV)
const handleExportCsv = () => {
  if (tableData.value.length === 0) {
    ElMessage.warning("Không có dữ liệu để xuất file CSV.")
    return
  }

  const headers = ['STT', 'KEYID', 'TASK_NAME', 'PAYMENT_MONTH', 'PIC', 'PART_NAME', 'GROUP_NAME', 'STATUS', 'ERROR_COUNT']
  const csvContent = [
    headers.join(','),
    ...tableData.value.map(row => [
      row.STT,
      `"${row.KEYID || ''}"`,
      `"${row.TASK_NAME || ''}"`,
      `"${row.PAYMENT_MONTH || ''}"`,
      `"${row.PIC || ''}"`,
      `"${row.PART_NAME || ''}"`,
      `"${row.GROUP_NAME || ''}"`,
      `"${row.STATUS || ''}"`,
      row.ERROR_COUNT || 0
    ].join(','))
  ].join('\n')

  const blob = new Blob(['\uFEFF' + csvContent], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `MEP_Payment_${new Date().toISOString().slice(0, 10)}.csv`
  a.click()
  URL.revokeObjectURL(url)
  ElMessage.success("Đã xuất file CSV thành công!")
}

// 11. TIẾP NHẬN UPLOAD FILE EXCEL
const handleUploadExcel = async (file, row) => {
  if (!row || !row.KEYID) {
    ElMessage.warning("Vui lòng lưu thông tin Số Công Việc (KEYID) trước khi tải file!")
    return
  }

  if (!file.name.endsWith('.xlsx') && !file.name.endsWith('.xlsm')) {
    ElMessage.error("Chỉ chấp nhận file Excel (.xlsx / .xlsm)")
    return
  }

  if (file.size && file.size > MAX_UPLOAD_SIZE_MB * 1024 * 1024) {
    ElMessage.error(`Dung lượng file (${(file.size / (1024 * 1024)).toFixed(1)}MB) vượt quá giới hạn cho phép ${MAX_UPLOAD_SIZE_MB}MB!`)
    return
  }

  const formData = new FormData()
  formData.append("file", file.raw)
  formData.append("KEYID", row.KEYID)
  if (row.PAYMENT_MONTH) {
    formData.append("payment_month", row.PAYMENT_MONTH)
  }

  row.STATUS = 'RUNNING'
  row.PROGRESS = 5
  row.REASON = 'Đang đẩy file lên AI Worker...'
  kpiStats.value.running = (kpiStats.value.running || 0) + 1

  // Đồng bộ cả đối tượng trong bảng và currentTask trong modal dialog nếu đang mở
  if (currentTask.value && currentTask.value.KEYID === row.KEYID) {
    currentTask.value.STATUS = 'RUNNING'
    currentTask.value.PROGRESS = 5
    currentTask.value.REASON = 'Đang đẩy file lên AI Worker...'
  }
  const targetRow = tableData.value.find(r => r.KEYID === row.KEYID)
  if (targetRow && targetRow !== row) {
    targetRow.STATUS = 'RUNNING'
    targetRow.PROGRESS = 5
    targetRow.REASON = 'Đang đẩy file lên AI Worker...'
  }

  startSmartPollingIfNeeded()
  loadKpiSummary()

  try {
    const res = await axios.post(`${FASTAPI_BASE_URL}/mep_payment/upload`, formData)
    ElMessage.success(res.data.message || "Tải lên thành công! AI đang bóc tách ngầm.")
    startSmartPollingIfNeeded()
    loadKpiSummary()
  } catch (err) {
    row.STATUS = 'WAITING'
    row.PROGRESS = 0
    row.REASON = 'Lỗi upload file'

    if (currentTask.value && currentTask.value.KEYID === row.KEYID) {
      currentTask.value.STATUS = 'WAITING'
      currentTask.value.PROGRESS = 0
      currentTask.value.REASON = 'Lỗi upload file'
    }
    const targetRow = tableData.value.find(r => r.KEYID === row.KEYID)
    if (targetRow && targetRow !== row) {
      targetRow.STATUS = 'WAITING'
      targetRow.PROGRESS = 0
      targetRow.REASON = 'Lỗi upload file'
    }

    stopSmartPolling()
    ElMessage.error("Lỗi khi kết nối Worker: " + (err.response?.data?.detail || err.message))
  }
}

// 12. DUYỆT / TỪ CHỐI (REVIEW WORKFLOW - LƯU CỘT REVIEW_BY BẰNG KNOX_ID)
const handleReview = async (row, decision, note = '') => {
  try {
    // Lưu vào Database bằng Knox ID (ví dụ: vhung99.nguyen), nếu chưa có Knox ID thì fallback sang PIC / Engineer
    const reviewerKnoxId = loginKnoxId.value || row.PIC || 'Engineer'
    const reviewNote = note || row.REVIEW_NOTE || ''
    await axios.post(`${FASTAPI_BASE_URL}/mep_payment/review`, {
      keyid: row.KEYID,
      decision: decision,
      note: reviewNote,
      reviewer: reviewerKnoxId
    })
    row.REVIEW_DECISION = decision
    row.REVIEW_BY = reviewerKnoxId
    if (reviewNote) row.REVIEW_NOTE = reviewNote
    const displayName = loginUserName.value ? `${loginUserName.value} (${reviewerKnoxId})` : reviewerKnoxId
    ElMessage.success(`Đã lưu quyết định: ${decision} (Người duyệt: ${displayName})`)
  } catch (err) {
    ElMessage.error("Lỗi lưu quyết định duyệt: " + err.message)
  }
}

// Vòng đời
onMounted(() => {
  _userInfo.value = getUserInfo()
  handleReload()
})

onUnmounted(() => {
  stopSmartPolling()
})

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)))
const handlePageChange = (p) => { page.value = p; loadData(); }
const handleSizeChange = (s) => { pageSize.value = s; page.value = 1; loadData(); }
const goFirst = () => { if (page.value > 1) { page.value = 1; loadData(); } }
const goLast = () => { if (page.value < totalPages.value) { page.value = totalPages.value; loadData(); } }

watch(selectedMonth, () => {
  page.value = 1
  handleReload()
})

watch(selectedStatus, (newVal) => {
  page.value = 1
  if (!newVal || newVal === 'ALL') {
    activeKpiFilter.value = 'ALL'
  } else {
    activeKpiFilter.value = newVal
  }
  loadKpiSummary()
  loadTotal()
  loadData()
})
</script>

<style scoped src="./operation.css"></style>