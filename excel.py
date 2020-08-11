import xlrd
import xlwt
from xlutils.copy import copy
import os,  logging

class xls_utls:

    def __init__(self, dir=None, file_name=None):
        self.file_path = os.path.join(dir, file_name)

    def create_sheet_with_titles(self, sheet_name, value):
        index = len(value)  # 获取需要写入数据的行数
        workbook = xlwt.Workbook()  # 新建一个工作簿
        sheet = workbook.add_sheet(sheet_name)  # 在工作簿中新建一个表格
        for i in range(0, index):
            for j in range(0, len(value[i])):
                sheet.write(i, j, value[i][j])  # 像表格中写入数据（对应的行和列）
        workbook.save(self.file_path)  # 保存工作簿
        logging.debug('xls写入成功')

    def write_excel_xls_append(self, sheet_name, value):
        index = len(value)  # 获取需要写入数据的行数
        workbook = xlrd.open_workbook(self.file_path)  # 打开工作簿
        worksheet = workbook.sheet_by_name(sheet_name)  # 获取工作簿中所有表格中的的第一个表格
        rows_old = worksheet.nrows  # 获取表格中已存在的数据的行数
        new_workbook = copy(workbook)  # 将xlrd对象拷贝转化为xlwt对象
        new_worksheet = new_workbook.get_sheet(0)  # 获取转化后工作簿中的第一个表格
        for i in range(0, index):
            for j in range(0, len(value[i])):
                new_worksheet.write(i + rows_old, j, value[i][j])  # 追加写入数据，注意是从i+rows_old行开始写入
        new_workbook.save(self.file_path)  # 保存工作簿
        logging.debug('xls追加写入成功')

    def read_excel_xls(self):
        pass


if __name__ == '__main__':
    book_name_xls = 'account_mate_data.xls'
    sheet_name_xls = 'account_mate_data'
    value_title = [["posts", "followers", "location"]]
    value1 = [[15, 110, ""],
              [20, 23, ""],
              [50, 90, ""],
              ]
    xls = xls_utls(dir='', file_name='account_mate_data.xls')
    xls.create_sheet_with_titles('account_mate_data', value_title)
    xls.write_excel_xls_append('account_mate_data', value1)