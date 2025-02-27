import tkinter as tk
from tkinter import simpledialog, messagebox
import pandas as pd
import os
import ast

# Load your reviews (can functionize - only do once)
df = pd.read_csv(r"C:\Users\qt321\Downloads\final_laptop_dataset.csv", header=None, names=['rating', 'review', 'asin', 'user_id', 'helpful_vote', 'verified_purchase', 'main_category', 'average_rating', 'price', 'os', 'color', 'brand', 'annotated'])
df['annotated'] = df['annotated'].fillna('')  # Fill NaNs with empty strings

# Create new df with full reviews instead of splitting into sentences
new_df = pd.DataFrame(columns=['raw_text'])
for index, row in df.iterrows():
    review = row['review'].strip()  # Lấy toàn bộ đoạn review
    if review:  # Chỉ thêm vào nếu review không rỗng
        new_df.loc[len(new_df)] = [review]

new_df.to_csv("sentences.csv", index=False)

class ABSAAnnotationApp:
    def __init__(self, master, df_path):
        self.master = master
        self.df_path = df_path
        self.load_data()
        self.current_index = self.find_first_unannotated_index()
        self.aspects = []
        self.category_list = set()  # Save entered categories list
        self.current_aspect = None  # Save aspect which has chosen for opinion labeling

        self.master.title("ABSA Annotation Tool")

        # Sentence display widget
        self.text_widget = tk.Text(self.master, wrap="word", height=10, width=60)
        self.text_widget.pack(padx=10, pady=10)

        # Widget to display annotated aspects
        self.aspect_display = tk.Text(self.master, wrap="word", height=8, width=60, bg="light gray")
        self.aspect_display.pack(padx=10, pady=5)
        self.aspect_display.insert("end", "Annotated Aspects:\n")
        self.aspect_display.configure(state="normal")  # Enable edit in widget

        # Entry field for category with placeholder
        self.category_entry = tk.Entry(self.master, width=30, fg="grey")
        self.category_entry.pack(pady=5)
        self.category_entry.insert(0, "Enter category")
        self.category_entry.bind("<FocusIn>", self.on_entry_focus_in)
        self.category_entry.bind("<FocusOut>", self.on_entry_focus_out)

        # Listbox for category history
        self.category_listbox = tk.Listbox(self.master, height=5, width=30)
        self.category_listbox.pack(pady=5)
        self.category_listbox.bind("<<ListboxSelect>>", self.fill_category_from_listbox)

        # Sentiment buttons
        self.pos_button = tk.Button(self.master, text="Positive", command=lambda: self.annotate_aspect("positive"))
        self.pos_button.pack(side="left", padx=5)

        self.neg_button = tk.Button(self.master, text="Negative", command=lambda: self.annotate_aspect("negative"))
        self.neg_button.pack(side="left", padx=5)

        self.neu_button = tk.Button(self.master, text="Neutral", command=lambda: self.annotate_aspect("neutral"))
        self.neu_button.pack(side="left", padx=5)

        # Button to annotate no aspect term
        self.noaspect_button = tk.Button(self.master, text="No Aspect Term", command=self.annotate_no_aspect)
        self.noaspect_button.pack(side="left", padx=5)

        # Button to annotate opinion
        self.opinion_button = tk.Button(self.master, text="Annotate Opinion", command=self.annotate_opinion)
        self.opinion_button.pack(side="left", padx=5)

        # Previous & Next sentence buttons in the same row
        nav_frame = tk.Frame(self.master)
        nav_frame.pack(pady=10)

        self.prev_button = tk.Button(nav_frame, text="Previous", command=self.save_and_previous)
        self.prev_button.pack(side="left", padx=5)

        self.next_button = tk.Button(nav_frame, text="Next", command=self.save_and_next)
        self.next_button.pack(side="left", padx=5)

        # Bind the aspect_display to update aspects when edited
        self.aspect_display.bind("<FocusOut>", self.update_aspects_from_display)

        self.load_sentence()

    def on_entry_focus_in(self, event):
        """Clear placeholder text when entry is focused."""
        if self.category_entry.get() == "Enter category":
            self.category_entry.delete(0, tk.END)
            self.category_entry.config(fg="black")

    def on_entry_focus_out(self, event):
        """Restore placeholder text if entry is empty."""
        if not self.category_entry.get():
            self.category_entry.insert(0, "Enter category")
            self.category_entry.config(fg="grey")

    def fill_category_from_listbox(self, event):
        """Fill the entry box when clicking a category in the listbox."""
        selected_index = self.category_listbox.curselection()
        if selected_index:
            category = self.category_listbox.get(selected_index)
            self.category_entry.delete(0, tk.END)
            self.category_entry.insert(0, category)
            self.category_entry.config(fg="black")

    def load_data(self):
        try:
            self.df = pd.read_csv(self.df_path)
            if 'aspectTerms' not in self.df.columns:
                self.df['aspectTerms'] = ''
            else:
                self.df['aspectTerms'].fillna('', inplace=True)
        except FileNotFoundError:
            self.df = pd.DataFrame(columns=['raw_text', 'aspectTerms'])

    def find_first_unannotated_index(self):
        unannotated = self.df[self.df['aspectTerms'] == ''].index
        if not unannotated.empty:
            return unannotated[0]
        return 0

    def load_sentence(self):
        if 0 <= self.current_index < len(self.df):
            sentence = self.df.iloc[self.current_index]["raw_text"]
            self.text_widget.delete(1.0, "end")
            self.text_widget.insert("end", sentence)
            # Load existing aspects if any
            self.aspects = ast.literal_eval(self.df.at[self.current_index, "aspectTerms"]) if self.df.at[self.current_index, "aspectTerms"] else []
            self.update_aspect_display()
        else:
            messagebox.showinfo("Completed", "All sentences have been annotated.")
            self.master.quit()

    def annotate_aspect(self, polarity):
        try:
            aspect = self.text_widget.selection_get()
            category = self.category_entry.get().strip()
            if category == "Enter category" or not category:
                category = "NULL"
            else:
                self.update_category_list(category)  # Update category list
            self.current_aspect = {'term': aspect, 'category': category, 'opinion': 'NULL', 'polarity': polarity}
            self.aspects.append(self.current_aspect)
            self.update_aspect_display()
        except tk.TclError:
            messagebox.showwarning("Warning", "No text selected.")

    def annotate_no_aspect(self):
        """Handle the case where no aspect is found."""
        self.current_aspect = {'term': 'noaspectterm', 'category': 'NULL', 'opinion': 'NULL', 'polarity': 'none'}
        self.aspects.append(self.current_aspect)
        self.update_aspect_display()

    def annotate_opinion(self):
        try:
            opinion = self.text_widget.selection_get()
            if self.current_aspect:
                self.current_aspect['opinion'] = opinion
                self.update_aspect_display()
            else:
                messagebox.showwarning("Warning", "Please select an aspect first.")
        except tk.TclError:
            messagebox.showwarning("Warning", "No text selected.")

    def update_aspect_display(self):
        self.aspect_display.delete("1.1", "end")  # Clear existing content
        self.aspect_display.insert("end", "Annotated Aspects:\n")
        for aspect in self.aspects:
            self.aspect_display.insert("end", f"{aspect}\n")

    def update_aspects_from_display(self, event=None):
        """Update the aspects list based on the content of aspect_display."""
        content = self.aspect_display.get("1.1", "end-1c")  # Get all content except the last newline
        lines = content.split("\n")[1:]  # Skip the first line ("Annotated Aspects:")
        self.aspects = []
        for line in lines:
            if line.strip():  # Skip empty lines
                try:
                    # Convert the string representation of the dictionary back to a dictionary
                    aspect = ast.literal_eval(line.strip())
                    self.aspects.append(aspect)
                except (ValueError, SyntaxError):
                    # Handle invalid lines (e.g., manual edits that are not valid dictionaries)
                    pass

    def save_and_next(self):
        self.update_aspects_from_display()  # Update aspects from display before saving
        self.df.at[self.current_index, "aspectTerms"] = str(self.aspects) if self.aspects else "[]"
        self.current_index += 1
        self.save_progress()
        self.load_sentence()

    def save_and_previous(self):
        self.update_aspects_from_display()  # Update aspects from display before saving
        self.df.at[self.current_index, "aspectTerms"] = str(self.aspects) if self.aspects else "[]"
        if self.current_index > 0:
            self.current_index -= 1
            self.save_progress()
            self.load_sentence()

    def save_progress(self):
        self.df.to_csv("annotated_sentences.csv", index=False)

    def update_category_list(self, category):
        """Thêm category mới vào listbox nếu chưa có."""
        if category not in self.category_list:
            self.category_list.add(category)
            self.category_listbox.insert(tk.END, category)

root = tk.Tk()
if os.path.exists("annotated_sentences.csv"):
    app = ABSAAnnotationApp(root, "annotated_sentences.csv")
else:
    app = ABSAAnnotationApp(root, "sentences.csv")
root.mainloop()