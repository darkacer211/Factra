from pandas import read_csv

# Read existing dataset
fd = read_csv("../data/news_dataset.csv")
print("Original Shape:", fd.shape)

# Drop missing values
fd = fd.dropna()
print("Shape after dropping NA:", fd.shape)
