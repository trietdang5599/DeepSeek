import ast
import tkinter as tk
from tkinter import messagebox
import pandas as pd
import os

# Loading initial review data from first CSV file and create sentences.csv file include 'raw_text' column
df = pd.read_csv(r"data/data_test.csv", header=None, names=['',	'rating', 'title', 'text',	'images', 'asin', 'parent_asin', 'user_id',	'timestamp',
                                                            	'helpful_vote',	'verified_purchase', 'main_category', 'average_rating', 'price',
                                                                'os', 'color', 'brand','annotated'])
df['annotated'] = df['annotated'].fillna('')  # Fill NaNs with empty strings

new_df = pd.DataFrame(columns=['text'])
for index, row in df.iterrows():
    review = row['text'].strip()
    if review:
        new_df.loc[len(new_df)] = [review]
new_df.to_csv("sentences.csv", index=False)

class ABSA_Annotation_App:
    def __init__(self, master, df_path):
        self.master = master
        self.df_path = df_path
        self.load_data()
        self.current_index = self.find_first_unannotated_index()  # Current index of unannotated sentence
        self.spans = []         # List lưu các annotation (span) với cấu trúc đầy đủ: tag, start, end, annotation
        self.current_span = None  # Span được chọn hiện tại

        self.master.title("ABSA Annotation Tool")

        # Text widget hiển thị câu hiện tại
        self.text_widget = tk.Text(self.master, wrap="word", height=10, width=60)
        self.text_widget.pack(padx=10, pady=10)
        self.text_widget.bind("<Button-1>", self.on_text_click)

        # Widget hiển thị thông tin các span đã annotate
        self.span_display = tk.Text(self.master, wrap="word", height=8, width=60, bg="light gray")
        self.span_display.pack(padx=10, pady=5)
        self.span_display.insert("end", "Annotated Spans with Aspects:\n")
        self.span_display.configure(state="normal")

        # Entry nhập category với placeholder
        self.category_entry = tk.Entry(self.master, width=30, fg="grey")
        self.category_entry.pack(pady=5)
        self.category_entry.insert(0, "Enter category")
        self.category_entry.bind("<FocusIn>", self.on_entry_focus_in)
        self.category_entry.bind("<FocusOut>", self.on_entry_focus_out)

        # Listbox cho lịch sử nhập category
        self.category_listbox = tk.Listbox(self.master, height=5, width=30)
        self.category_listbox.pack(pady=5)
        self.category_listbox.bind("<<ListboxSelect>>", self.fill_category_from_listbox)

        # Các nút: annotate span, update category
        button_frame = tk.Frame(self.master)
        button_frame.pack(pady=5)
        self.span_button = tk.Button(button_frame, text="Span", command=self.annotate_span)
        self.span_button.pack(side="left", padx=5)
        self.update_category_button = tk.Button(button_frame, text="Update Category", command=self.update_category_label)
        self.update_category_button.pack(side="left", padx=5)

        # Các nút annotate aspect (theo sentiment)
        aspect_frame = tk.Frame(self.master)
        aspect_frame.pack(pady=5)
        self.pos_button = tk.Button(aspect_frame, text="Aspect Positive",
                                    command=lambda: self.annotate_aspect("positive"))
        self.pos_button.pack(side="left", padx=5)
        self.neg_button = tk.Button(aspect_frame, text="Aspect Negative",
                                    command=lambda: self.annotate_aspect("negative"))
        self.neg_button.pack(side="left", padx=5)
        self.neu_button = tk.Button(aspect_frame, text="Aspect Neutral",
                                    command=lambda: self.annotate_aspect("neutral"))
        self.neu_button.pack(side="left", padx=5)

        # Nút annotate opinion
        self.opinion_button = tk.Button(self.master, text="Opinion", command=self.annotate_opinion)
        self.opinion_button.pack(side="left", padx=5)

        # Các nút điều hướng: Previous và Next
        nav_frame = tk.Frame(self.master)
        nav_frame.pack(pady=10)
        self.prev_button = tk.Button(nav_frame, text="Previous", command=self.save_and_previous)
        self.prev_button.pack(side="left", padx=5)
        self.next_button = tk.Button(nav_frame, text="Next", command=self.save_and_next)
        self.next_button.pack(side="left", padx=5)

        self.load_sentence()

    def on_entry_focus_in(self, event):
        if self.category_entry.get() == "Enter category":
            self.category_entry.delete(0, tk.END)
            self.category_entry.config(fg="black")

    def on_entry_focus_out(self, event):
        if not self.category_entry.get():
            self.category_entry.insert(0, "Enter category")
            self.category_entry.config(fg="grey")

    def fill_category_from_listbox(self, event):
        selected_index = self.category_listbox.curselection()
        if selected_index:
            category = self.category_listbox.get(selected_index)
            self.category_entry.delete(0, tk.END)
            self.category_entry.insert(0, category)
            self.category_entry.config(fg="black")

    def load_data(self):
        try:
            self.df = pd.read_csv(self.df_path)
            # Nếu cột labels chưa tồn tại, tạo mới cột này
            if 'labels' not in self.df.columns:
                self.df['labels'] = ''
            else:
                self.df['labels'].fillna('', inplace=True)
        except FileNotFoundError:
            self.df = pd.DataFrame(columns=['text', 'labels'])

    def find_first_unannotated_index(self):
        unannotated = self.df[self.df['labels'] == ''].index
        if not unannotated.empty:
            return unannotated[0]
        return 0

    def load_sentence(self):
        if 0 <= self.current_index < len(self.df):
            sentence = self.df.iloc[self.current_index]["text"]
            self.text_widget.delete("1.0", "end")
            self.text_widget.insert("end", sentence)
            # Xóa hết các tag cũ (nếu có)
            for tag in self.text_widget.tag_names():
                self.text_widget.tag_delete(tag)

            # Reset lại danh sách spans và current_span
            self.spans = []
            self.current_span = None

            # Nếu câu hiện tại đã có annotation, load lại chúng
            if self.df.at[self.current_index, "labels"]:
                try:
                    saved = ast.literal_eval(self.df.at[self.current_index, "labels"])
                    if isinstance(saved, dict):
                        self.spans = saved.get('spans', [])
                    elif isinstance(saved, list):
                        self.spans = saved
                    else:
                        self.spans = []
                    for span in self.spans:
                        tag = span['tag']
                        start = span['start']
                        end = span['end']
                        self.text_widget.tag_add(tag, start, end)
                        # Lấy category và opinion để xác định màu sắc
                        category = span.get('annotation', {}).get('category', "NULL")
                        opinion = span.get('annotation', {}).get('opinion', "NULL")
                        color = "green" if category != "NULL" and opinion != "NULL" else "blue"
                        self.text_widget.tag_configure(tag, foreground=color)
                        self.text_widget.tag_bind(tag, "<Button-1>", self.on_span_click)
                except Exception as e:
                    print("Error loading saved spans with their aspects", e)
            self.update_span_display()
        else:
            messagebox.showinfo("Completed", "All sentences have been annotated.")
            self.master.quit()

    def annotate_span(self):
        try:
            span_text = self.text_widget.selection_get()
            start = self.text_widget.index("sel.first")
            end = self.text_widget.index("sel.last")

            # Lấy category từ ô nhập (mặc định là "NULL")
            category = self.category_entry.get().strip() if self.category_entry.get().strip() != "Enter category" else "NULL"

            tag_name = f"span_{len(self.spans)}"
            self.text_widget.tag_add(tag_name, start, end)
            self.text_widget.tag_configure(tag_name, foreground="blue")
            self.text_widget.tag_bind(tag_name, "<Button-1>", self.on_span_click)

            # Tạo annotation đầy đủ cho span
            annotation = {
                'span': span_text,
                'term': 'noaspectterm',
                'category': category,
                'opinion': 'NULL',
                'polarity': None
            }
            # Lưu thông tin của span dưới dạng dictionary
            span = {'tag': tag_name, 'start': start, 'end': end, 'annotation': annotation}
            self.spans.append(span)
            self.current_span = span
            self.update_span_display()
        except tk.TclError:
            messagebox.showwarning("Warning", "No sentence selected for span annotation.")

    def update_category_label(self):
        """Cập nhật 'category' của annotation cho span được chọn"""
        if self.current_span:
            new_category = self.category_entry.get().strip() if self.category_entry.get().strip() != "Enter category" else "NULL"
            self.current_span['annotation']['category'] = new_category
            tag = self.current_span['tag']
            # Đổi màu: green nếu có cả category và opinion hợp lệ, blue nếu chưa đủ
            color = "green" if new_category != "NULL" and self.current_span['annotation'].get('opinion', "NULL") != "NULL" else "blue"
            self.text_widget.tag_configure(tag, foreground=color)
            self.update_span_display()
        else:
            messagebox.showwarning("Warning", "No span selected to update.")

    def annotate_aspect(self, polarity):
        """Cập nhật trường 'term' và 'polarity' của annotation cho span đã chọn"""
        try:
            aspect_text = self.text_widget.selection_get()
            if self.current_span:
                self.current_span['annotation']['term'] = aspect_text
                self.current_span['annotation']['polarity'] = polarity
                self.update_span_display()
            else:
                messagebox.showwarning("Warning", "Please select a span first.")
        except tk.TclError:
            messagebox.showwarning("Warning", "No text selected for aspect annotation.")

    def annotate_opinion(self):
        """Cập nhật trường 'opinion' của annotation cho span đã chọn"""
        try:
            opinion_text = self.text_widget.selection_get()
            if self.current_span:
                self.current_span['annotation']['opinion'] = opinion_text
                # Cập nhật màu hiển thị sau khi cập nhật opinion
                tag = self.current_span['tag']
                category = self.current_span['annotation'].get('category', "NULL")
                color = "green" if category != "NULL" and opinion_text != "" else "blue"
                self.text_widget.tag_configure(tag, foreground=color)
                self.update_span_display()
            else:
                messagebox.showwarning("Warning", "Please select a span first.")
        except tk.TclError:
            messagebox.showwarning("Warning", "No text selected for opinion annotation.")

    def on_span_click(self, event):
        """Khi click vào một span, đặt span đó là span được chọn hiện tại."""
        index = self.text_widget.index(f"@{event.x},{event.y}")
        for span in self.spans:
            if self.text_widget.compare(index, ">=", span['start']) and self.text_widget.compare(index, "<", span['end']):
                self.current_span = span
                self.update_span_display()
                break

    def on_text_click(self, event):
        """Nếu click ngoài các span, reset current_span."""
        index = self.text_widget.index(f"@{event.x},{event.y}")
        found = False
        for span in self.spans:
            if self.text_widget.compare(index, ">=", span['start']) and self.text_widget.compare(index, "<", span['end']):
                found = True
                break
        if not found:
            self.current_span = None

    # def update_span_display(self):
    #     """Cập nhật widget hiển thị các span đã annotate."""
    #     self.span_display.config(state="normal")
    #     self.span_display.delete("1.0", tk.END)
    #     self.span_display.insert(tk.END, "Annotated Spans with Aspects:\n")
    #     for span in self.spans:
    #         self.span_display.insert(tk.END, f"{span['annotation']}\n\n")
    #     if self.current_span:
    #         meta = {k: self.current_span[k] for k in ['tag', 'start', 'end']}
    #         self.span_display.insert(tk.END, f"\nSelected Span:\n{meta}")
    #     self.span_display.config(state="disabled")

    def update_span_display(self):
        self.span_display.config(state="normal")
        self.span_display.delete("1.0", "end")
        self.span_display.insert("end", "Annotated Spans with Aspects:\n")
        for span in self.spans:
            # Nếu span không có key 'annotation', gán giá trị mặc định dựa trên dữ liệu hiện có
            annotation = span.get('annotation')
            if annotation is None:
                annotation = {
                    'span': span.get('span', ''),
                    'term': span.get('term', 'noaspectterm'),
                    'category': span.get('category', 'NULL'),
                    'opinion': span.get('opinion', 'NULL'),
                    'polarity': span.get('polarity', None)
                }
            self.span_display.insert("end", f"{annotation}\n\n")
        if self.current_span:
            meta = {k: self.current_span[k] for k in ['tag', 'start', 'end']}
            self.span_display.insert("end", f"Selected Span:\n{meta}")
        self.span_display.config(state="disabled")

    def update_spans_from_display(self, event=None):
        """Nếu cần chỉnh sửa thủ công trong aspect_display, cập nhật lại danh sách spans.
           Lưu ý: Phương thức này cần được điều chỉnh sao cho phù hợp với định dạng hiển thị."""
        content = self.span_display.get("1.0", "end-1c")
        lines = content.split("\n")[1:]  # Bỏ dòng tiêu đề
        updated_spans = []
        for line in lines:
            if line.strip():
                try:
                    span = ast.literal_eval(line.strip())
                    updated_spans.append(span)
                except (ValueError, SyntaxError):
                    pass
        self.spans = updated_spans

    def save_and_next(self):
        self.update_spans_from_display()  # Nếu có chỉnh sửa thủ công
        # Lưu annotation vào cột "labels" dưới dạng dictionary có key 'spans'
        self.df.at[self.current_index, "labels"] = str({'spans': self.spans}) if self.spans else "[]"
        self.current_index += 1
        self.save_progress()
        self.load_sentence()

    def save_and_previous(self):
        self.update_spans_from_display()
        self.df.at[self.current_index, "labels"] = str({'spans': self.spans}) if self.spans else "[]"
        if self.current_index > 0:
            self.current_index -= 1
        self.save_progress()
        self.load_sentence()

    def save_progress(self):
        self.df.to_csv("annotated_sentences.csv", index=False)

if __name__ == "__main__":
    root = tk.Tk()
    if os.path.exists("annotated_sentences.csv"):
        app = ABSA_Annotation_App(root, "annotated_sentences.csv")
    else:
        app = ABSA_Annotation_App(root, "sentences.csv")
    root.mainloop()
