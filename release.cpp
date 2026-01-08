#include<bits/stdc++.h>
using namespace std;

struct Date
{
    int year;
    int month;
    int day;
    Date():year(1970),month(1),day(1){}
    Date(string str)
    {
        sscanf(str.c_str(),"### %d.%d.%d",&year,&month,&day);
        if(year<1970||month<1||month>12||day<1||day>31)
        {
            year=1970;
            month=1;
            day=1;
        }
    }
    bool operator<(const Date& other)const
    {
        if(year!=other.year)
            return year<other.year;
        if(month!=other.month)
            return month<other.month;
        return day<other.day;
    }
    bool operator==(const Date& other)const
    {
        return year==other.year&&month==other.month&&day==other.day;
    }
};

struct Passage
{
    string title;
    string content;
    Date date;
    static vector<Passage> passages;
    bool operator<(const Passage& other)const
    {
        if(date==other.date)
            return title<other.title;
        return date<other.date;
    }
};
vector<Passage> Passage::passages;

bool ReadLine(ifstream& fin,string& line)
{
    if(getline(fin,line))
    {
        if(line.back()=='\r')
            line.pop_back();
        return 1;
    }
    return 0;
}

void ReadPassages(const string& Filename)
{
    ifstream fin(Filename);
    if(!fin.is_open())
    {
        cerr<<"Cannot open file "<<Filename<<endl;
        return ;
    }
    string line;
    Date date;
    ReadLine(fin,line);
    while(true)
    {
        istringstream iss(line);
        string word;
        iss>>word;
        if(word=="###")
        {
            date=Date(line);
            ReadLine(fin,line);
            continue;
        }
        if(word=="####")
        {
            Passage p;
            bool endup=1;
            p.date=date;
            p.title=line.substr(5);
            while(ReadLine(fin,line))
            {
                if(line.substr(0,5)=="#### "||line.substr(0,4)=="### ")
                {
                    endup=0;
                    break;
                }
                p.content+=line+"\n";
            }
            Passage::passages.push_back(p);
            if(!endup)
                continue;
            fin.close();
            return ;
        }
        if(line.empty())
        {
            ReadLine(fin,line);
            continue;
        }
        cerr<<"undefined line:"<<line<<'|'<<endl;
        if(ReadLine(fin,line))
            continue;
        fin.close();
        return ;
    }
}

void FetchFiles()
{
    string path="./MarkdownFiles/",file;
    ifstream fin("filelist.txt");
    while(ReadLine(fin,file))
    {
        cerr<<"Reading "<<file<<" ... ";
        ReadPassages(path+file);
        cerr<<"Done."<<endl;
    }
}

void MergeFiles()
{
    cerr<<"Merging files ... ";
    sort(Passage::passages.begin(),Passage::passages.end());
    ofstream fout("release.md");
    Date prevDate;
    for(auto& p:Passage::passages)
    {
        if(!(p.date==prevDate))
            fout<<"### "<<p.date.year<<"."<<p.date.month<<"."<<p.date.day<<"\n";
        fout<<"#### "<<p.title<<"\n";
        fout<<p.content;
        prevDate=p.date;
    }
    fout.close();
    cerr<<"Done."<<endl;
}

void TransformToPDF()
{
    cerr<<"Transforming to PDF ... ";
    system("pandoc -s -o Release.pdf --pdf-engine=xelatex release.md");
    cerr<<"Done."<<endl;
}

signed main(int argc, char** argv)
{
    vector<string> args(argv,argv+argc);
    FetchFiles();
    MergeFiles();
    // TransformToPDF();
    return 0;
}