<template>
  <div class="mx-auto w-full max-w-[1800px] space-y-4">
    <section
      class="rounded-2xl border border-surface-200/70 bg-gradient-to-r from-surface-50 via-surface-0 to-primary-50/30 px-4 py-4 shadow-sm dark:border-surface-700/70 dark:from-surface-900/80 dark:via-surface-900 dark:to-primary-900/20"
    >
      <div class="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
        <div class="space-y-0.5">
          <h2 class="text-xl font-bold tracking-tight text-surface-900 dark:text-surface-0">Issue 工作台</h2>
          <p class="text-xs text-surface-600 dark:text-surface-300">跨审查问题视图，支持筛选、批量状态更新与快速处理</p>
        </div>
        <div class="grid grid-cols-2 gap-2 sm:grid-cols-4">
          <div class="rounded-xl border border-surface-200/70 bg-white/80 px-3 py-1.5 dark:border-surface-700/70 dark:bg-surface-900/70">
            <p class="text-[11px] text-surface-500 dark:text-surface-400">总记录</p>
            <p class="text-base font-semibold text-surface-900 dark:text-surface-0">{{ total }}</p>
          </div>
          <div class="rounded-xl border border-surface-200/70 bg-white/80 px-3 py-1.5 dark:border-surface-700/70 dark:bg-surface-900/70">
            <p class="text-[11px] text-surface-500 dark:text-surface-400">当前页</p>
            <p class="text-base font-semibold text-surface-900 dark:text-surface-0">{{ findings.length }}</p>
          </div>
          <div class="rounded-xl border border-surface-200/70 bg-white/80 px-3 py-1.5 dark:border-surface-700/70 dark:bg-surface-900/70">
            <p class="text-[11px] text-surface-500 dark:text-surface-400">已选项</p>
            <p class="text-base font-semibold text-surface-900 dark:text-surface-0">{{ selectedCount }}</p>
          </div>
          <div class="rounded-xl border border-surface-200/70 bg-white/80 px-3 py-1.5 dark:border-surface-700/70 dark:bg-surface-900/70">
            <p class="text-[11px] text-surface-500 dark:text-surface-400">生效筛选</p>
            <p class="text-base font-semibold text-surface-900 dark:text-surface-0">{{ activeFiltersCount }}</p>
          </div>
        </div>
      </div>
    </section>

    <Card class="border border-surface-200/70 shadow-sm dark:border-surface-700/70">
      <template #content>
        <div class="space-y-2.5">
          <div class="flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
            <div class="flex flex-wrap items-center gap-2">
              <div class="inline-flex items-center gap-2 text-xs font-medium text-surface-700 dark:text-surface-200">
                <span class="inline-flex h-2 w-2 rounded-full bg-primary-500" />
                查询筛选
              </div>
              <Tag
                v-if="activeFiltersCount > 0"
                severity="contrast"
                class="text-[11px] dark:!bg-surface-700 dark:!text-surface-200"
              >
                已启用 {{ activeFiltersCount }} 项
              </Tag>
            </div>
            <div class="flex flex-wrap items-center gap-2">
              <Button label="重置筛选" outlined size="small" :disabled="loading" @click="resetFilters" />
              <Button label="查询 Issue" size="small" :loading="loading" @click="handleSearch" />
            </div>
          </div>

          <div class="rounded-xl border border-surface-200/70 bg-surface-50/45 p-2.5 dark:border-surface-700/60 dark:bg-surface-800/25">
            <div class="grid grid-cols-1 gap-2 md:grid-cols-2 xl:[grid-template-columns:1.2fr_0.85fr_0.9fr_0.9fr_1.35fr_1.1fr]">
              <label class="flex flex-col gap-1">
                <span class="text-[11px] font-medium text-surface-600 dark:text-surface-300">项目</span>
                <Select
                  v-model="selectedProjectId"
                  :options="projectOptions"
                  option-label="label"
                  option-value="value"
                  class="filter-control w-full"
                  placeholder="全部项目"
                />
              </label>

              <label class="flex flex-col gap-1">
                <span class="text-[11px] font-medium text-surface-600 dark:text-surface-300">严重度</span>
                <Select
                  v-model="selectedSeverity"
                  :options="severityOptions"
                  option-label="label"
                  option-value="value"
                  class="filter-control w-full"
                  placeholder="全部严重度"
                />
              </label>

              <label class="flex flex-col gap-1">
                <span class="text-[11px] font-medium text-surface-600 dark:text-surface-300">审查状态</span>
                <Select
                  v-model="selectedReviewStatus"
                  :options="reviewStatusOptions"
                  option-label="label"
                  option-value="value"
                  class="filter-control w-full"
                  placeholder="全部状态"
                />
              </label>

              <label class="flex flex-col gap-1">
                <span class="text-[11px] font-medium text-surface-600 dark:text-surface-300">处理状态</span>
                <Select
                  v-model="selectedActionStatus"
                  :options="actionStatusOptions"
                  option-label="label"
                  option-value="value"
                  class="filter-control w-full"
                  placeholder="全部处理状态"
                />
              </label>

              <label class="flex flex-col gap-1">
                <span class="text-[11px] font-medium text-surface-600 dark:text-surface-300">时间范围</span>
                <DatePicker
                  v-model="selectedTimeRange"
                  selectionMode="range"
                  dateFormat="yy年mm月dd日"
                  showIcon
                  iconDisplay="input"
                  class="filter-control w-full"
                  placeholder="选择开始与结束日期"
                />
              </label>

              <label class="flex flex-col gap-1">
                <span class="text-[11px] font-medium text-surface-600 dark:text-surface-300">作者</span>
                <Select
                  v-model="selectedAuthor"
                  :options="authorOptions"
                  option-label="label"
                  option-value="value"
                  class="filter-control w-full"
                  placeholder="全部作者"
                  filter
                />
              </label>
            </div>
          </div>
        </div>
      </template>
    </Card>

    <Card class="border border-surface-200/70 shadow-sm dark:border-surface-700/70">
      <template #content>
        <div class="mb-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div class="text-sm font-medium text-surface-700 dark:text-surface-200">
            Issue 列表
            <span class="ml-2 text-xs font-normal text-surface-500 dark:text-surface-400">共 {{ total }} 条</span>
          </div>
          <div class="text-xs text-surface-500 dark:text-surface-400">第 {{ currentPage }} / {{ totalPages }} 页</div>
        </div>

        <div class="relative max-h-[74vh] overflow-auto rounded-xl border border-surface-200/70 dark:border-surface-700/70">
          <table class="w-full min-w-[1440px] text-sm text-surface-800 dark:text-surface-100">
            <thead>
              <tr class="sticky top-0 z-[1] border-b border-surface-200/70 bg-surface-50/95 text-left text-xs font-semibold uppercase tracking-wide text-surface-600 backdrop-blur dark:border-surface-600/70 dark:bg-surface-800/95 dark:text-surface-200">
                <th class="w-10 px-2 py-3">
                  <Checkbox
                    binary
                    :model-value="isCurrentPageAllSelected"
                    :indeterminate="isCurrentPagePartiallySelected && !isCurrentPageAllSelected"
                    @change="toggleSelectAllCurrentPage"
                  />
                </th>
                <th class="px-2 py-3 whitespace-nowrap">项目</th>
                <th class="px-2 py-3 whitespace-nowrap">MR</th>
                <th class="min-w-[260px] px-2 py-3">文件/行</th>
                <th class="px-2 py-3 whitespace-nowrap">严重度</th>
                <th class="min-w-[280px] px-2 py-3">问题描述</th>
                <th class="px-2 py-3 whitespace-nowrap">作者</th>
                <th class="px-2 py-3 whitespace-nowrap">审查状态</th>
                <th class="px-2 py-3 whitespace-nowrap">处理状态</th>
                <th class="px-2 py-3 whitespace-nowrap">最近处理</th>
                <th class="px-2 py-3 text-right whitespace-nowrap">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="row in findings"
                :key="row.id"
                class="border-b border-surface-100/80 align-top transition hover:bg-surface-50/70 dark:border-surface-700/70 dark:hover:bg-surface-700/55"
              >
                <td class="px-2 py-4">
                  <Checkbox binary :model-value="isSelected(row.id)" @change="toggleSelectRow(row.id)" />
                </td>
                <td class="px-2 py-4 whitespace-nowrap text-surface-800 dark:text-surface-100">{{ row.review.project_name || '-' }}</td>
                <td class="px-2 py-4 whitespace-nowrap">
                  <div class="space-y-1">
                    <Tag class="whitespace-nowrap" severity="info">!{{ row.review.merge_request_iid }}</Tag>
                    <button
                      type="button"
                      class="block whitespace-nowrap text-xs text-primary hover:underline"
                      @click="goToReview(row.review.id)"
                    >
                      审查 #{{ row.review.id }}
                    </button>
                  </div>
                </td>
                <td class="px-2 py-4">
                  <div class="max-w-[320px] space-y-1">
                    <div
                      class="truncate text-xs font-semibold text-surface-800 dark:text-surface-100"
                      :title="row.file_path || '-'"
                    >
                      {{ fileNameFromPath(row.file_path) }}
                    </div>
                    <div
                      class="truncate font-mono text-[11px] text-surface-500 dark:text-surface-400"
                      :title="row.file_path || '-'"
                    >
                      {{ row.file_path || '-' }}
                    </div>
                    <Tag class="whitespace-nowrap text-[11px]" severity="contrast">{{ formatLineRange(row.line_start, row.line_end) }}</Tag>
                  </div>
                </td>
                <td class="px-2 py-4 whitespace-nowrap">
                  <Tag class="whitespace-nowrap" :severity="severityTag(row.severity)">{{ severityLabel(row.severity) }}</Tag>
                </td>
                <td class="px-2 py-4">
                  <p class="line-clamp-3 leading-5 text-surface-800 dark:text-surface-100">{{ row.message || '-' }}</p>
                </td>
                <td class="px-2 py-4 whitespace-nowrap text-surface-700 dark:text-surface-200">{{ row.review.author_name || row.review.author_email || '-' }}</td>
                <td class="px-2 py-4 whitespace-nowrap">
                  <Tag class="whitespace-nowrap" :severity="reviewStatusSeverity(row.review.status)">{{ reviewStatusLabel(row.review.status) }}</Tag>
                </td>
                <td class="px-2 py-4 whitespace-nowrap">
                  <Tag class="whitespace-nowrap" :severity="actionStatusSeverity(row.action_status)">{{ actionStatusLabel(row.action_status) }}</Tag>
                </td>
                <td class="px-2 py-4 whitespace-nowrap text-xs text-surface-600 dark:text-surface-300">
                  <template v-if="row.latest_action">
                    <div class="font-medium text-surface-700 dark:text-surface-200">{{ row.latest_action.actor || '-' }}</div>
                    <div>{{ formatDisplayTime(row.latest_action.action_at) }}</div>
                  </template>
                  <span v-else>-</span>
                </td>
                <td class="px-2 py-4 text-right">
                  <div class="flex justify-end gap-1 whitespace-nowrap">
                    <Button size="small" text @click="openDetailDialog(row)">详情</Button>
                    <Button
                      v-if="canShowRowAction(row, 'todo')"
                      size="small"
                      text
                      severity="warn"
                      :loading="rowActionLoadingId === row.id"
                      @click="submitRowAction(row.id, 'todo')"
                    >
                      待办
                    </Button>
                    <Button
                      v-if="canShowRowAction(row, 'fixed')"
                      size="small"
                      text
                      severity="success"
                      :loading="rowActionLoadingId === row.id"
                      @click="submitRowAction(row.id, 'fixed')"
                    >
                      修复
                    </Button>
                    <Button
                      v-if="canShowRowAction(row, 'ignored')"
                      size="small"
                      text
                      severity="secondary"
                      :loading="rowActionLoadingId === row.id"
                      @click="openIgnoreDialog([row.id])"
                    >
                      忽略
                    </Button>
                    <Button
                      v-if="canShowRowAction(row, 'reopened')"
                      size="small"
                      text
                      severity="info"
                      :loading="rowActionLoadingId === row.id"
                      @click="submitRowAction(row.id, 'reopened')"
                    >
                      重开
                    </Button>
                  </div>
                </td>
              </tr>
              <tr v-if="!loading && findings.length === 0">
                <td colspan="11" class="px-3 py-10 text-center text-surface-500 dark:text-surface-400">暂无符合条件的问题记录</td>
              </tr>
            </tbody>
          </table>

          <div v-if="loading" class="absolute inset-0 z-10 flex items-center justify-center bg-white/70 backdrop-blur-[1px] dark:bg-surface-900/70">
            <div class="inline-flex items-center gap-2 rounded-lg border border-surface-200 bg-white px-3 py-2 text-surface-600 shadow-sm dark:border-surface-700 dark:bg-surface-900 dark:text-surface-200">
              <Loader2 class="h-4 w-4 animate-spin" />
              加载中...
            </div>
          </div>
        </div>

        <div class="mt-4 flex flex-col gap-3 border-t border-surface-200/60 pt-4 sm:flex-row sm:items-center sm:justify-between dark:border-surface-700/60">
          <span class="text-xs text-surface-500 dark:text-surface-400">共 {{ total }} 条记录</span>
          <Paginator
            class="w-full sm:w-auto"
            :first="paginatorFirst"
            :rows="pageSize"
            :totalRecords="total"
            :rowsPerPageOptions="rowsPerPageOptions"
            :template="paginatorTemplate"
            currentPageReportTemplate="第 {currentPage} / {totalPages} 页，共 {totalRecords} 条"
            @page="handlePaginatorPage"
          />
        </div>
      </template>
    </Card>

    <Dialog
      v-model:visible="detailDialogVisible"
      modal
      header="Issue 详情"
      :style="{ width: 'min(980px, 96vw)' }"
      :breakpoints="{ '1024px': '96vw', '760px': '99vw' }"
    >
      <div v-if="detailRow" class="max-h-[78vh] space-y-3 overflow-auto pr-0.5">
        <section class="rounded-lg border border-surface-200/70 bg-surface-50/60 p-3 dark:border-surface-700/70 dark:bg-surface-800/40">
          <div class="flex flex-wrap items-start justify-between gap-2">
            <div class="space-y-1">
              <div class="text-xs text-surface-500 dark:text-surface-400">文件 / 行</div>
              <div class="font-mono text-xs text-surface-700 dark:text-surface-200">{{ detailRow.file_path || '-' }}</div>
              <Tag class="whitespace-nowrap text-[11px]" severity="contrast">{{ formatLineRange(detailRow.line_start, detailRow.line_end) }}</Tag>
            </div>
            <div class="flex flex-wrap items-center gap-2">
              <Tag class="whitespace-nowrap" :severity="severityTag(detailRow.severity)">严重度：{{ severityLabel(detailRow.severity) }}</Tag>
              <Tag class="whitespace-nowrap" :severity="reviewStatusSeverity(detailRow.review.status)">审查：{{ reviewStatusLabel(detailRow.review.status) }}</Tag>
              <Tag class="whitespace-nowrap" :severity="actionStatusSeverity(detailRow.action_status)">处理：{{ actionStatusLabel(detailRow.action_status) }}</Tag>
            </div>
          </div>

          <div class="mt-3 grid grid-cols-1 gap-2 md:grid-cols-3">
            <div class="rounded-md border border-surface-200/70 bg-white p-2 dark:border-surface-700/70 dark:bg-surface-900/70">
              <div class="text-xs text-surface-500 dark:text-surface-400">项目</div>
              <div class="mt-0.5 text-sm font-medium text-surface-800 dark:text-surface-100">{{ detailRow.review.project_name || '-' }}</div>
            </div>
            <div class="rounded-md border border-surface-200/70 bg-white p-2 dark:border-surface-700/70 dark:bg-surface-900/70">
              <div class="text-xs text-surface-500 dark:text-surface-400">作者</div>
              <div class="mt-0.5 text-sm font-medium text-surface-800 dark:text-surface-100">{{ detailRow.review.author_name || detailRow.review.author_email || '-' }}</div>
            </div>
            <div class="rounded-md border border-surface-200/70 bg-white p-2 dark:border-surface-700/70 dark:bg-surface-900/70">
              <div class="text-xs text-surface-500 dark:text-surface-400">MR / 审查</div>
              <div class="mt-1 flex items-center gap-2">
                <Tag severity="info" class="whitespace-nowrap">!{{ detailRow.review.merge_request_iid }}</Tag>
                <button
                  type="button"
                  class="text-xs text-primary hover:underline"
                  @click="goToReview(detailRow.review.id)"
                >
                  审查 #{{ detailRow.review.id }}
                </button>
              </div>
            </div>
          </div>
        </section>

        <div class="grid grid-cols-1 gap-3 xl:grid-cols-[1.5fr_1fr]">
          <div class="space-y-3">
            <section class="rounded-lg border border-surface-200/70 bg-surface-50/60 p-3 dark:border-surface-700/70 dark:bg-surface-800/40">
              <div class="mb-1 text-xs text-surface-500 dark:text-surface-400">问题描述</div>
              <p class="max-h-56 overflow-auto whitespace-pre-wrap text-sm leading-6 text-surface-800 dark:text-surface-100">{{ detailRow.message || '-' }}</p>
            </section>

            <section class="rounded-lg border border-surface-200/70 bg-surface-50/60 p-3 dark:border-surface-700/70 dark:bg-surface-800/40">
              <div class="mb-1 text-xs text-surface-500 dark:text-surface-400">问题代码</div>
              <pre
                v-if="detailRow.code_snippet"
                class="max-h-96 overflow-auto whitespace-pre-wrap rounded-md bg-slate-900 p-3 text-xs leading-5 text-slate-100"
              ><code>{{ detailRow.code_snippet }}</code></pre>
              <div v-else class="text-sm text-surface-600 dark:text-surface-300">暂无问题代码</div>
            </section>
          </div>

          <div class="space-y-3">
            <section class="rounded-lg border border-surface-200/70 bg-surface-50/60 p-3 dark:border-surface-700/70 dark:bg-surface-800/40">
              <div class="mb-2 flex items-center justify-between">
                <div class="text-xs font-medium text-surface-500 dark:text-surface-400">快速处理</div>
                <div class="text-xs text-surface-500 dark:text-surface-400">处理人：{{ currentActorName }}</div>
              </div>
              <Textarea
                v-model="detailActionNote"
                rows="2"
                autoResize
                class="w-full"
                placeholder="处理备注（可选）"
              />
              <div class="mt-2 flex flex-wrap gap-2">
                <Button
                  v-if="canShowDetailAction('todo')"
                  size="small"
                  severity="warn"
                  outlined
                  :loading="detailActionLoading"
                  label="待处理"
                  @click="submitDetailAction('todo')"
                />
                <Button
                  v-if="canShowDetailAction('fixed')"
                  size="small"
                  severity="success"
                  outlined
                  :loading="detailActionLoading"
                  label="已修复"
                  @click="submitDetailAction('fixed')"
                />
                <Button
                  v-if="canShowDetailAction('ignored')"
                  size="small"
                  severity="secondary"
                  outlined
                  :loading="detailActionLoading"
                  label="忽略"
                  @click="openIgnoreDialog([detailRow.id], detailActionNote)"
                />
                <Button
                  v-if="canShowDetailAction('reopened')"
                  size="small"
                  severity="info"
                  outlined
                  :loading="detailActionLoading"
                  label="重新打开"
                  @click="submitDetailAction('reopened')"
                />
              </div>
            </section>

            <section class="rounded-lg border border-surface-200/70 bg-surface-50/60 p-3 dark:border-surface-700/70 dark:bg-surface-800/40">
              <div class="mb-1 text-xs text-surface-500 dark:text-surface-400">最近处理</div>
              <template v-if="detailRow.latest_action">
                <div class="text-sm font-medium text-surface-800 dark:text-surface-100">{{ detailRow.latest_action.actor || '-' }}</div>
                <div class="text-xs text-surface-500 dark:text-surface-400">{{ formatDisplayTime(detailRow.latest_action.action_at) }}</div>
                <p class="mt-1 whitespace-pre-wrap text-sm text-surface-700 dark:text-surface-200">{{ detailRow.latest_action.note || '无备注' }}</p>
              </template>
              <div v-else class="text-sm text-surface-600 dark:text-surface-300">暂无处理记录</div>
            </section>

            <section class="rounded-lg border border-surface-200/70 bg-surface-50/60 p-3 dark:border-surface-700/70 dark:bg-surface-800/40">
              <div class="mb-1 text-xs text-surface-500 dark:text-surface-400">处理历史</div>
              <div v-if="actionHistoryLoading" class="text-sm text-surface-600 dark:text-surface-300">加载中...</div>
              <div v-else-if="actionHistory.length === 0" class="text-sm text-surface-600 dark:text-surface-300">暂无历史记录</div>
              <div v-else class="max-h-72 space-y-2 overflow-auto pr-1">
                <div
                  v-for="item in actionHistory"
                  :key="item.id"
                  class="rounded-md border border-surface-200/80 bg-white/80 p-2 text-xs dark:border-surface-700/70 dark:bg-surface-900/60"
                >
                  <div class="mb-1 flex flex-wrap items-center gap-2">
                    <Tag :severity="actionStatusSeverity(item.action_type)" class="whitespace-nowrap">{{ actionStatusLabel(item.action_type) }}</Tag>
                    <span class="font-medium text-surface-700 dark:text-surface-200">{{ item.actor || '-' }}</span>
                    <span class="text-surface-500 dark:text-surface-400">{{ formatDisplayTime(item.action_at) }}</span>
                  </div>
                  <div v-if="item.ignore_reason_code" class="mb-1 text-surface-600 dark:text-surface-300">
                    忽略原因：{{ ignoreReasonLabel(item.ignore_reason_code) }}
                    <span v-if="item.ignore_reason_note">（{{ item.ignore_reason_note }}）</span>
                  </div>
                  <div v-if="item.note" class="whitespace-pre-wrap text-surface-700 dark:text-surface-200">{{ item.note }}</div>
                </div>
              </div>
            </section>
          </div>
        </div>
      </div>
    </Dialog>

    <Dialog
      v-model:visible="ignoreDialogVisible"
      modal
      header="忽略原因"
      :style="{ width: 'min(520px, 95vw)' }"
    >
      <div class="space-y-3">
        <div class="rounded-lg border border-surface-200/70 bg-surface-50/60 p-2.5 text-xs text-surface-600 dark:border-surface-700/70 dark:bg-surface-800/40 dark:text-surface-300">
          将忽略 {{ ignoreTargetIds.length }} 条 Issue，请填写结构化原因。
        </div>

        <label class="flex flex-col gap-1">
          <span class="text-xs font-medium text-surface-600 dark:text-surface-300">忽略原因</span>
          <Select
            v-model="ignoreReasonCode"
            :options="ignoreReasonOptions"
            option-label="label"
            option-value="value"
            class="w-full"
            placeholder="请选择忽略原因"
          />
        </label>

        <label class="flex flex-col gap-1">
          <span class="text-xs font-medium text-surface-600 dark:text-surface-300">
            原因备注
            <span v-if="isIgnoreReasonNoteRequired" class="text-red-500">*</span>
          </span>
          <Textarea
            v-model="ignoreReasonNote"
            rows="3"
            autoResize
            class="w-full"
            placeholder="当原因为“暂缓修复”或“其他”时必填"
          />
        </label>
      </div>
      <template #footer>
        <div class="flex justify-end gap-2">
          <Button label="取消" text :disabled="ignoreSubmitting" @click="closeIgnoreDialog" />
          <Button label="确认忽略" severity="secondary" :loading="ignoreSubmitting" @click="confirmIgnoreAction" />
        </div>
      </template>
    </Dialog>

    <Transition
      enter-active-class="transform-gpu transition duration-200 ease-out"
      enter-from-class="translate-y-4 opacity-0"
      enter-to-class="translate-y-0 opacity-100"
      leave-active-class="transform-gpu transition duration-150 ease-in"
      leave-from-class="translate-y-0 opacity-100"
      leave-to-class="translate-y-4 opacity-0"
    >
      <div v-if="selectedCount > 0" class="pointer-events-none fixed inset-x-0 bottom-4 z-40 px-3 sm:px-6">
        <div
          class="pointer-events-auto mx-auto w-full max-w-[1200px] rounded-2xl border border-primary-200/80 bg-gradient-to-r from-white/95 via-white/95 to-primary-50/75 shadow-xl shadow-primary-200/20 backdrop-blur-sm dark:border-primary-800/70 dark:from-surface-900/95 dark:via-surface-900/95 dark:to-primary-950/35 dark:shadow-primary-950/20"
          :class="isCompactBatchPanel ? 'p-2.5' : 'p-3'"
        >
          <div
            class="flex flex-col xl:grid xl:items-start"
            :class="isCompactBatchPanel ? 'gap-2.5 xl:grid-cols-[1.55fr_1fr]' : 'gap-3 xl:grid-cols-[1.45fr_1fr]'"
          >
            <div :class="isCompactBatchPanel ? 'space-y-2.5' : 'space-y-3'">
              <div class="flex flex-wrap items-center justify-between gap-2">
                <div class="flex flex-wrap items-center gap-2">
                  <div class="inline-flex items-center gap-2 text-sm font-semibold text-surface-800 dark:text-surface-100">
                    <span class="inline-flex h-2 w-2 rounded-full bg-primary-500" />
                    批量操作
                  </div>
                  <Tag severity="contrast" class="text-[11px] dark:!bg-surface-700 dark:!text-surface-200">已选 {{ selectedCount }} 项</Tag>
                  <Tag severity="info" class="text-[11px]">当前页 {{ selectedOnPageCount }} 项</Tag>
                </div>
                <div class="flex flex-wrap items-center gap-1.5">
                  <div class="inline-flex items-center gap-1 rounded-lg border border-surface-200/80 bg-white/80 p-0.5 dark:border-surface-700/80 dark:bg-surface-900/70">
                    <Button
                      size="small"
                      label="标准"
                      :text="batchPanelDensity !== 'standard'"
                      :severity="batchPanelDensity === 'standard' ? 'primary' : 'secondary'"
                      :disabled="batchLoading"
                      @click="setBatchPanelDensity('standard')"
                    />
                    <Button
                      size="small"
                      label="紧凑"
                      :text="batchPanelDensity !== 'compact'"
                      :severity="batchPanelDensity === 'compact' ? 'primary' : 'secondary'"
                      :disabled="batchLoading"
                      @click="setBatchPanelDensity('compact')"
                    />
                  </div>
                  <Button
                    size="small"
                    text
                    icon="pi pi-times"
                    label="清空选择"
                    :disabled="batchLoading"
                    @click="clearSelection"
                  />
                </div>
              </div>
              <div class="grid grid-cols-1 sm:grid-cols-2" :class="isCompactBatchPanel ? 'gap-1.5' : 'gap-2'">
                <Button
                  size="small"
                  severity="success"
                  icon="pi pi-check-circle"
                  label="标记已修复"
                  :loading="batchLoading"
                  :disabled="!isBatchActionEnabled('fixed')"
                  @click="submitBatchAction('fixed')"
                />
                <Button
                  size="small"
                  severity="warn"
                  icon="pi pi-clock"
                  label="标记待处理"
                  :loading="batchLoading"
                  :disabled="!isBatchActionEnabled('todo')"
                  @click="submitBatchAction('todo')"
                />
                <Button
                  size="small"
                  severity="secondary"
                  icon="pi pi-eye-slash"
                  label="标记已忽略"
                  :loading="batchLoading"
                  :disabled="!isBatchActionEnabled('ignored')"
                  @click="openIgnoreDialog(selectedIds)"
                />
                <Button
                  size="small"
                  severity="info"
                  icon="pi pi-refresh"
                  label="标记重新打开"
                  :loading="batchLoading"
                  :disabled="!isBatchActionEnabled('reopened')"
                  @click="submitBatchAction('reopened')"
                />
              </div>
            </div>
            <div
              class="w-full rounded-xl border border-surface-200/80 bg-white/80 dark:border-surface-700/80 dark:bg-surface-900/70"
              :class="isCompactBatchPanel ? 'p-2.5' : 'p-3'"
            >
              <div class="text-xs font-medium text-surface-600 dark:text-surface-300" :class="isCompactBatchPanel ? 'mb-1.5' : 'mb-2'">处理信息</div>
              <div class="grid grid-cols-1" :class="isCompactBatchPanel ? 'gap-1.5' : 'gap-2'">
                <label class="flex flex-col gap-1">
                  <span class="text-[11px] font-medium text-surface-500 dark:text-surface-400">处理人</span>
                  <InputText :model-value="currentActorName" class="filter-control w-full" readonly />
                </label>
                <label class="flex flex-col gap-1">
                  <span class="text-[11px] font-medium text-surface-500 dark:text-surface-400">处理备注</span>
                  <Textarea
                    v-model="actionNote"
                    :rows="isCompactBatchPanel ? 1 : 2"
                    autoResize
                    class="w-full"
                    placeholder="可选，填写处理说明"
                  />
                </label>
                <div v-if="!isCompactBatchPanel" class="text-[11px] text-surface-500 dark:text-surface-400">
                  仅会处理状态可变更的 Issue，已忽略/已修复等不适用项会自动跳过
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Loader2 } from 'lucide-vue-next'
import { createReviewFindingActionsBatch, getProjects, getReviewFindingActions, getReviewFindingsList, getReviews } from '@/api/index'
import { formatBackendDateTime } from '@/utils/datetime'
import { getReviewStatusMeta } from '@/utils/reviewStatus'
import { useAuthStore } from '@/stores/auth'
import { toast } from '@/utils/toast'
import Button from 'primevue/button'
import Card from 'primevue/card'
import Checkbox from 'primevue/checkbox'
import DatePicker from 'primevue/datepicker'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Paginator from 'primevue/paginator'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import Textarea from 'primevue/textarea'

type FindingActionType = 'fixed' | 'ignored' | 'todo' | 'reopened'
type FindingActionStatus = FindingActionType | 'unprocessed'
type IgnoreReasonCode = 'business_exception' | 'historical_debt' | 'rule_false_positive' | 'defer_fix' | 'duplicate' | 'other'

interface WorkbenchReviewMeta {
  id: number
  project_id: number
  project_name: string
  merge_request_iid: number
  merge_request_title: string
  author_name: string
  author_email: string
  status: string
  created_at: string | null
}

interface WorkbenchActionMeta {
  id: number
  finding_id: number
  action_type: string
  actor: string
  note: string
  ignore_reason_code?: string
  ignore_reason_note?: string
  action_at: string | null
}

interface IgnoreReasonOption {
  label: string
  value: IgnoreReasonCode
}

interface WorkbenchFinding {
  id: number
  review_id: number
  severity: string
  file_path: string
  line_start: number | null
  line_end: number | null
  message: string
  code_snippet: string
  created_at: string | null
  action_status: string
  latest_action: WorkbenchActionMeta | null
  review: WorkbenchReviewMeta
}

interface ProjectOption {
  label: string
  value: number | null
}

interface AuthorOption {
  label: string
  value: string
}

type BatchPanelDensity = 'standard' | 'compact'

const router = useRouter()
const auth = useAuthStore()
auth.hydrate()

const loading = ref(false)
const batchLoading = ref(false)
const rowActionLoadingId = ref<number | null>(null)
const detailDialogVisible = ref(false)
const detailRow = ref<WorkbenchFinding | null>(null)
const actionHistoryLoading = ref(false)
const actionHistory = ref<WorkbenchActionMeta[]>([])
const ignoreDialogVisible = ref(false)
const ignoreSubmitting = ref(false)
const ignoreTargetIds = ref<number[]>([])
const ignoreReasonCode = ref<IgnoreReasonCode | ''>('')
const ignoreReasonNote = ref('')
const ignoreActionNote = ref<string | null>(null)
const detailActionNote = ref('')

const findings = ref<WorkbenchFinding[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)

const selectedIds = ref<number[]>([])

const selectedProjectId = ref<number | null>(null)
const selectedSeverity = ref('')
const selectedReviewStatus = ref('')
const selectedActionStatus = ref('')
const selectedAuthor = ref('')
const selectedTimeRange = ref<(Date | null)[] | null>(null)

const actionNote = ref('')
const batchPanelDensity = ref<BatchPanelDensity>('standard')

const projectOptions = ref<ProjectOption[]>([{ label: '全部项目', value: null }])
const authorOptions = ref<AuthorOption[]>([{ label: '全部作者', value: '' }])

const severityOptions = [
  { label: '全部严重度', value: '' },
  { label: '阻断 (critical)', value: 'critical' },
  { label: '严重 (high)', value: 'high' },
  { label: '中等 (medium)', value: 'medium' },
  { label: '轻微 (low)', value: 'low' },
]

const reviewStatusOptions = [
  { label: '全部状态', value: '' },
  { label: '等待中', value: 'pending' },
  { label: '进行中', value: 'processing' },
  { label: '已完成', value: 'completed' },
  { label: '失败', value: 'failed' },
]

const actionStatusOptions = [
  { label: '全部处理状态', value: '' },
  { label: '未处理', value: 'unprocessed' },
  { label: '已修复', value: 'fixed' },
  { label: '待处理', value: 'todo' },
  { label: '已忽略', value: 'ignored' },
  { label: '重新打开', value: 'reopened' },
]

const rowsPerPageOptions = [10, 20, 50, 100]
const paginatorTemplate = {
  '640px': 'PrevPageLink CurrentPageReport NextPageLink',
  '960px': 'FirstPageLink PrevPageLink CurrentPageReport NextPageLink LastPageLink RowsPerPageDropdown',
  default: 'FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink RowsPerPageDropdown JumpToPageInput CurrentPageReport',
}

const ignoreReasonOptions: IgnoreReasonOption[] = [
  { label: '业务特例', value: 'business_exception' },
  { label: '历史债务', value: 'historical_debt' },
  { label: '规则误报', value: 'rule_false_positive' },
  { label: '暂缓修复', value: 'defer_fix' },
  { label: '重复问题', value: 'duplicate' },
  { label: '其他', value: 'other' },
]

const selectedCount = computed(() => selectedIds.value.length)
const currentActorName = computed(() => auth.username || 'admin')
const isIgnoreReasonNoteRequired = computed(() => ignoreReasonCode.value === 'defer_fix' || ignoreReasonCode.value === 'other')
const findingById = computed(() => new Map(findings.value.map((item) => [item.id, item])))
const detailActionLoading = computed(() => {
  const findingId = detailRow.value?.id
  return findingId != null && rowActionLoadingId.value === findingId
})

const totalPages = computed(() => {
  const pages = Math.ceil(total.value / pageSize.value)
  return Math.max(pages, 1)
})
const paginatorFirst = computed(() => Math.max((currentPage.value - 1) * pageSize.value, 0))
const isCompactBatchPanel = computed(() => batchPanelDensity.value === 'compact')

const currentPageIds = computed(() => findings.value.map((item) => item.id))
const selectedOnPageCount = computed(() => currentPageIds.value.filter((id) => selectedIds.value.includes(id)).length)
const activeFiltersCount = computed(() => {
  let count = 0
  if (selectedProjectId.value != null) count += 1
  if (selectedSeverity.value) count += 1
  if (selectedReviewStatus.value) count += 1
  if (selectedActionStatus.value) count += 1
  if (selectedAuthor.value) count += 1
  if (Array.isArray(selectedTimeRange.value) && selectedTimeRange.value.some((item) => item instanceof Date)) count += 1
  return count
})

const isCurrentPageAllSelected = computed(() => {
  if (currentPageIds.value.length === 0) return false
  return currentPageIds.value.every((id) => selectedIds.value.includes(id))
})

const isCurrentPagePartiallySelected = computed(() => {
  if (currentPageIds.value.length === 0) return false
  const selectedOnPage = currentPageIds.value.filter((id) => selectedIds.value.includes(id)).length
  return selectedOnPage > 0 && selectedOnPage < currentPageIds.value.length
})

const clearSelection = () => {
  selectedIds.value = []
}

const BATCH_PANEL_DENSITY_STORAGE_KEY = 'issue-workbench-batch-panel-density'

const setBatchPanelDensity = (density: BatchPanelDensity) => {
  batchPanelDensity.value = density
  try {
    window.localStorage.setItem(BATCH_PANEL_DENSITY_STORAGE_KEY, density)
  } catch (error) {
    console.warn('保存批量操作面板密度失败:', error)
  }
}

const hydrateBatchPanelDensity = () => {
  try {
    const stored = window.localStorage.getItem(BATCH_PANEL_DENSITY_STORAGE_KEY)
    if (stored === 'compact' || stored === 'standard') {
      batchPanelDensity.value = stored
    }
  } catch (error) {
    console.warn('读取批量操作面板密度失败:', error)
  }
}

const getRangeTimeIso = (index: 0 | 1): string | undefined => {
  const range = selectedTimeRange.value
  if (!Array.isArray(range) || range.length <= index) return undefined
  const value = range[index]
  if (!(value instanceof Date) || Number.isNaN(value.getTime())) return undefined
  const normalized = new Date(value)
  if (index === 0) {
    normalized.setHours(0, 0, 0, 0)
  } else {
    normalized.setHours(23, 59, 59, 999)
  }
  return normalized.toISOString()
}

const fetchProjects = async () => {
  try {
    const unique = new Map<number, ProjectOption>()
    let page = 1
    let expectedTotal = 0
    let loadedCount = 0
    const maxPages = 200

    while (page <= maxPages) {
      const resp = await getProjects({ page })
      const results = Array.isArray(resp?.results) ? resp.results : []
      expectedTotal = Number(resp?.count || expectedTotal || 0)
      if (results.length === 0) break

      for (const item of results) {
        const projectId = typeof item?.project_id === 'number' ? item.project_id : null
        if (projectId == null) continue
        unique.set(projectId, {
          label: String(item?.project_name || `项目 ${projectId}`),
          value: projectId,
        })
      }

      loadedCount += results.length
      if (expectedTotal > 0 && loadedCount >= expectedTotal) break
      page += 1
    }

    projectOptions.value = [{ label: '全部项目', value: null }, ...[...unique.values()].sort((a, b) => a.label.localeCompare(b.label))]
  } catch (error) {
    console.error('获取项目列表失败:', error)
  }
}

const fetchAuthors = async () => {
  try {
    const unique = new Map<string, AuthorOption>()
    let page = 1
    let expectedTotal = 0
    let loadedCount = 0
    const pageSize = 100
    const maxPages = 200

    while (page <= maxPages) {
      const offset = (page - 1) * pageSize
      const resp = await getReviews({ limit: pageSize, offset })
      const results = Array.isArray(resp?.results) ? resp.results : []
      expectedTotal = Number(resp?.total || resp?.count || expectedTotal || 0)
      if (results.length === 0) break

      for (const item of results) {
        const authorName = String(item?.author_name || '').trim()
        const authorEmail = String(item?.author_email || '').trim()
        const value = authorEmail || authorName
        if (!value) continue
        const label = authorName && authorEmail ? `${authorName} (${authorEmail})` : authorName || authorEmail
        unique.set(value, { label, value })
      }

      loadedCount += results.length
      if (expectedTotal > 0 && loadedCount >= expectedTotal) break
      page += 1
    }

    authorOptions.value = [{ label: '全部作者', value: '' }, ...[...unique.values()].sort((a, b) => a.label.localeCompare(b.label))]
  } catch (error) {
    console.error('获取作者列表失败:', error)
  }
}

const fetchFindings = async (allowClamp: boolean = true) => {
  loading.value = true
  clearSelection()
  try {
    const params = {
      page: currentPage.value,
      limit: pageSize.value,
      project_id: selectedProjectId.value ?? undefined,
      severities: selectedSeverity.value || undefined,
      review_statuses: selectedReviewStatus.value || undefined,
      action_statuses: selectedActionStatus.value || undefined,
      author: selectedAuthor.value || undefined,
      start_at: getRangeTimeIso(0),
      end_at: getRangeTimeIso(1),
    }

    const resp = await getReviewFindingsList(params)
    findings.value = Array.isArray(resp?.results) ? resp.results : []
    total.value = Number(resp?.total || resp?.count || 0)
    if (allowClamp) {
      const pages = Math.max(Math.ceil(total.value / pageSize.value), 1)
      if (currentPage.value > pages) {
        currentPage.value = pages
        await fetchFindings(false)
        return
      }
    }
  } catch (error: any) {
    console.error('获取 Issue 工作台列表失败:', error)
    toast.error(error?.response?.data?.detail || '获取 Issue 工作台列表失败')
    findings.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  currentPage.value = 1
  fetchFindings()
}

const resetFilters = () => {
  selectedProjectId.value = null
  selectedSeverity.value = ''
  selectedReviewStatus.value = ''
  selectedActionStatus.value = ''
  selectedAuthor.value = ''
  selectedTimeRange.value = null
  currentPage.value = 1
  fetchFindings()
}

const handlePaginatorPage = (event: { page: number; rows: number }) => {
  const nextPage = event.page + 1
  const nextPageSize = event.rows
  const shouldFetch = nextPage !== currentPage.value || nextPageSize !== pageSize.value
  if (!shouldFetch) return
  currentPage.value = nextPage
  pageSize.value = nextPageSize
  fetchFindings()
}

const isSelected = (id: number): boolean => selectedIds.value.includes(id)

const toggleSelectRow = (id: number) => {
  if (isSelected(id)) {
    selectedIds.value = selectedIds.value.filter((item) => item !== id)
    return
  }
  selectedIds.value = [...selectedIds.value, id]
}

const toggleSelectAllCurrentPage = () => {
  if (isCurrentPageAllSelected.value) {
    selectedIds.value = []
    return
  }
  selectedIds.value = [...currentPageIds.value]
}

const extractErrorMessage = (error: any, fallback: string): string => {
  const data = error?.response?.data
  return String(data?.message || data?.detail || fallback)
}

const normalizeActionStatus = (status: string): FindingActionStatus => {
  const normalized = String(status || '').toLowerCase()
  if (normalized === 'fixed' || normalized === 'todo' || normalized === 'ignored' || normalized === 'reopened') {
    return normalized
  }
  return 'unprocessed'
}

const canApplyActionForStatus = (status: string, actionType: FindingActionType): boolean => {
  const normalizedStatus = normalizeActionStatus(status)
  if (actionType === 'reopened') return normalizedStatus !== 'unprocessed' && normalizedStatus !== 'reopened'
  if (actionType === 'ignored') return normalizedStatus !== 'ignored'
  if (actionType === 'fixed') return normalizedStatus !== 'fixed'
  if (actionType === 'todo') return normalizedStatus !== 'todo'
  return true
}

const canShowRowAction = (row: WorkbenchFinding, actionType: FindingActionType): boolean =>
  canApplyActionForStatus(row.action_status, actionType)

const getActionableSelectedIds = (actionType: FindingActionType): number[] =>
  selectedIds.value.filter((id) => {
    const finding = findingById.value.get(id)
    return Boolean(finding && canApplyActionForStatus(finding.action_status, actionType))
  })

const isBatchActionEnabled = (actionType: FindingActionType): boolean =>
  !batchLoading.value && getActionableSelectedIds(actionType).length > 0

const canShowDetailAction = (actionType: FindingActionType): boolean => {
  if (!detailRow.value) return false
  return canShowRowAction(detailRow.value, actionType)
}

const syncDetailStateAfterAction = (findingId: number) => {
  if (!detailDialogVisible.value || detailRow.value?.id !== findingId) return
  const refreshed = findings.value.find((item) => item.id === findingId)
  if (refreshed) {
    detailRow.value = refreshed
  }
  void fetchActionHistory(findingId)
}

const doBatchAction = async (
  actionType: FindingActionType,
  ids: number[],
  options?: {
    ignoreReasonCode?: IgnoreReasonCode
    ignoreReasonNote?: string
    note?: string
  },
) => {
  if (ids.length === 0) {
    toast.warning('请先选择要处理的记录')
    return false
  }

  try {
    const resp = await createReviewFindingActionsBatch({
      finding_ids: ids,
      action_type: actionType,
      note: typeof options?.note === 'string' ? options.note.trim() : actionNote.value.trim(),
      ignore_reason_code: options?.ignoreReasonCode,
      ignore_reason_note: options?.ignoreReasonNote?.trim() || '',
    })

    const successCount = Number(resp?.success_count || 0)
    const failedCount = Number(resp?.failed_count || 0)
    if (failedCount > 0) {
      toast.warning(`批量处理完成，成功 ${successCount} 条，失败 ${failedCount} 条`)
    } else {
      toast.success(`批量处理成功，共 ${successCount} 条`)
    }
    return true
  } catch (error: any) {
    console.error('批量处理失败:', error)
    toast.error(extractErrorMessage(error, '批量处理失败'))
    return false
  }
}

const submitBatchAction = async (actionType: FindingActionType) => {
  const actionableIds = getActionableSelectedIds(actionType)
  if (actionableIds.length === 0) {
    toast.warning('所选 Issue 当前状态不支持该操作')
    return
  }
  if (actionType === 'ignored') {
    openIgnoreDialog(actionableIds)
    return
  }
  if (actionType === 'reopened') {
    const confirmed = window.confirm(`确认重新打开 ${actionableIds.length} 条 Issue 吗？`)
    if (!confirmed) return
  }
  batchLoading.value = true
  try {
    const ok = await doBatchAction(actionType, actionableIds)
    if (!ok) return
    actionNote.value = ''
    clearSelection()
    await fetchFindings()
  } finally {
    batchLoading.value = false
  }
}

const submitRowAction = async (
  id: number,
  actionType: FindingActionType,
  options?: {
    note?: string
    preserveSelection?: boolean
  },
): Promise<boolean> => {
  const finding = findingById.value.get(id)
  if (finding && !canApplyActionForStatus(finding.action_status, actionType)) {
    toast.warning('当前状态不支持该操作')
    return false
  }
  if (actionType === 'ignored') {
    openIgnoreDialog([id], options?.note)
    return false
  }
  if (actionType === 'reopened') {
    const confirmed = window.confirm('确认将该问题重新打开吗？')
    if (!confirmed) return false
  }
  rowActionLoadingId.value = id
  try {
    const ok = await doBatchAction(actionType, [id], { note: options?.note })
    if (!ok) return false
    if (typeof options?.note !== 'string') {
      actionNote.value = ''
    }
    if (!options?.preserveSelection) {
      clearSelection()
    }
    await fetchFindings()
    syncDetailStateAfterAction(id)
    return true
  } finally {
    rowActionLoadingId.value = null
  }
}

const submitDetailAction = async (actionType: FindingActionType) => {
  const findingId = detailRow.value?.id
  if (findingId == null) return
  const ok = await submitRowAction(
    findingId,
    actionType,
    { note: detailActionNote.value, preserveSelection: true },
  )
  if (ok) {
    detailActionNote.value = ''
  }
}

const goToReview = (reviewId: number) => {
  router.push(`/reviews/${reviewId}`)
}

const fetchActionHistory = async (findingId: number) => {
  actionHistoryLoading.value = true
  actionHistory.value = []
  try {
    const resp = await getReviewFindingActions(findingId)
    actionHistory.value = Array.isArray(resp?.results) ? resp.results : []
  } catch (error) {
    console.error('获取处理历史失败:', error)
    toast.error(extractErrorMessage(error, '获取处理历史失败'))
  } finally {
    actionHistoryLoading.value = false
  }
}

const openDetailDialog = (row: WorkbenchFinding) => {
  detailRow.value = row
  detailDialogVisible.value = true
  detailActionNote.value = ''
  void fetchActionHistory(row.id)
}

const closeIgnoreDialog = () => {
  ignoreDialogVisible.value = false
  ignoreTargetIds.value = []
  ignoreReasonCode.value = ''
  ignoreReasonNote.value = ''
  ignoreActionNote.value = null
}

const openIgnoreDialog = (ids: number[], note?: string) => {
  const normalizedIds = Array.from(new Set(ids.filter((item) => Number.isFinite(item) && item > 0)))
  if (normalizedIds.length === 0) {
    toast.warning('请先选择要处理的记录')
    return
  }
  const actionableIds = normalizedIds.filter((id) => {
    const finding = findingById.value.get(id)
    return !finding || canApplyActionForStatus(finding.action_status, 'ignored')
  })
  if (actionableIds.length === 0) {
    toast.warning('所选 Issue 当前状态不支持忽略')
    return
  }
  ignoreTargetIds.value = actionableIds
  ignoreReasonCode.value = ''
  ignoreReasonNote.value = ''
  ignoreActionNote.value = typeof note === 'string' ? note.trim() : null
  ignoreDialogVisible.value = true
}

const confirmIgnoreAction = async () => {
  const reasonCode = ignoreReasonCode.value
  if (!reasonCode) {
    toast.warning('请选择忽略原因')
    return
  }
  const reasonNote = ignoreReasonNote.value.trim()
  if (isIgnoreReasonNoteRequired.value && !reasonNote) {
    toast.warning('当前忽略原因必须填写备注')
    return
  }

  ignoreSubmitting.value = true
  batchLoading.value = true
  const targetIds = [...ignoreTargetIds.value]
  if (targetIds.length === 1) {
    rowActionLoadingId.value = targetIds[0]
  }
  try {
    const ok = await doBatchAction(
      'ignored',
      targetIds,
      {
        ignoreReasonCode: reasonCode,
        ignoreReasonNote: reasonNote,
        note: ignoreActionNote.value ?? undefined,
      },
    )
    if (!ok) return
    if (ignoreActionNote.value == null) {
      actionNote.value = ''
    } else {
      detailActionNote.value = ''
    }
    if (!detailDialogVisible.value) {
      clearSelection()
    }
    closeIgnoreDialog()
    await fetchFindings()
    if (detailDialogVisible.value && targetIds.length === 1) {
      syncDetailStateAfterAction(targetIds[0])
    }
  } finally {
    ignoreSubmitting.value = false
    batchLoading.value = false
    rowActionLoadingId.value = null
  }
}

const formatLineRange = (lineStart: number | null, lineEnd: number | null): string => {
  if (lineStart == null) return '行号 -'
  if (lineEnd != null && lineEnd !== lineStart) return `L${lineStart}-L${lineEnd}`
  return `L${lineStart}`
}

const fileNameFromPath = (path: string | null | undefined): string => {
  const raw = String(path || '').trim()
  if (!raw) return '-'
  const normalized = raw.replace(/\\/g, '/')
  const segments = normalized.split('/').filter(Boolean)
  return segments.length > 0 ? segments[segments.length - 1] : normalized
}

const severityTag = (severity: string): 'danger' | 'warn' | 'success' | 'secondary' => {
  const normalized = String(severity || '').toLowerCase()
  if (normalized === 'critical' || normalized === 'high') return 'danger'
  if (normalized === 'medium') return 'warn'
  if (normalized === 'low') return 'success'
  return 'secondary'
}

const severityLabel = (severity: string): string => {
  const normalized = String(severity || '').toLowerCase()
  if (normalized === 'critical') return '阻断'
  if (normalized === 'high') return '严重'
  if (normalized === 'medium') return '中等'
  if (normalized === 'low') return '轻微'
  return severity || '未知'
}

const actionStatusLabel = (status: string): string => {
  const normalized = normalizeActionStatus(status)
  if (normalized === 'unprocessed') return '未处理'
  if (normalized === 'fixed') return '已修复'
  if (normalized === 'todo') return '待处理'
  if (normalized === 'ignored') return '已忽略'
  if (normalized === 'reopened') return '重新打开'
  return status || '未知'
}

const actionStatusSeverity = (status: string): 'success' | 'warn' | 'info' | 'danger' | 'secondary' => {
  const normalized = normalizeActionStatus(status)
  if (normalized === 'fixed') return 'success'
  if (normalized === 'todo') return 'warn'
  if (normalized === 'reopened') return 'info'
  if (normalized === 'ignored') return 'danger'
  return 'secondary'
}

const ignoreReasonLabel = (code: string): string => {
  const normalized = String(code || '').toLowerCase()
  if (normalized === 'business_exception') return '业务特例'
  if (normalized === 'historical_debt') return '历史债务'
  if (normalized === 'rule_false_positive') return '规则误报'
  if (normalized === 'defer_fix') return '暂缓修复'
  if (normalized === 'duplicate') return '重复问题'
  if (normalized === 'other') return '其他'
  return code || '未标注'
}

const reviewStatusLabel = (status: string): string => getReviewStatusMeta(status).label
const reviewStatusSeverity = (status: string): 'success' | 'info' | 'danger' | 'warn' | 'secondary' => getReviewStatusMeta(status).severity

const formatDisplayTime = (value: string | null | undefined): string => formatBackendDateTime(value)

onMounted(() => {
  hydrateBatchPanelDensity()
  void fetchProjects()
  void fetchAuthors()
  void fetchFindings()
})
</script>

<style scoped>
.filter-control {
  min-height: 2.25rem;
}

:deep(.filter-control.p-inputtext),
:deep(.filter-control.p-select .p-select-label),
:deep(.filter-control.p-datepicker .p-inputtext) {
  padding-top: 0.5rem;
  padding-bottom: 0.5rem;
  font-size: 0.875rem;
  line-height: 1.25rem;
}

:deep(.filter-control.p-select .p-select-dropdown) {
  width: 2rem;
}
</style>
