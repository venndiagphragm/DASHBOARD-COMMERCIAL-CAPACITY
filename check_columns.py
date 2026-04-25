import pandas as pd

with open('columns.txt', 'w', encoding='utf-8') as out:
    df1 = pd.read_csv('Data Ruas Pipa dan Tarif MINYAK.csv', sep=';', encoding='latin1')
    out.write("--- Data Ruas Pipa ---\n")
    out.write(str(df1.columns.tolist()) + "\n")
    out.write(str(df1.head(2).to_dict('records')) + "\n\n")

    df2 = pd.read_csv('Data Volume & Realisasi minyak.csv', sep=';', encoding='latin1')
    out.write("--- Data Volume & Realisasi ---\n")
    out.write(str(df2.columns.tolist()) + "\n")
    out.write(str(df2.head(2).to_dict('records')) + "\n")
