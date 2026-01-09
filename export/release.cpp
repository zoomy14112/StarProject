#include<bits/stdc++.h>
using namespace std;
vector<string> Fliter;
mt19937 Rand(time(nullptr)^(uintptr_t)(new char));

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
    string ToString()const
    {
        char buffer[20];
        sprintf(buffer,"%d.%d.%d",year,month,day);
        return string(buffer);
    }
    friend bool IsConstant(const Date& d1,const Date& d2)
    {
        return d1.year==d2.year&&d1.month==d2.month;
    }
};

struct Passage
{
    string title;
    string content;
    Date date;
    int seed;
    static vector<Passage> passages;
    Passage()
    {
        seed=Rand();
        date=Date();
    }
    bool operator<(const Passage& other)const
    {
        if(date==other.date)
            return seed<other.seed;
        return date<other.date;
    }
    void SelfCheck()
    {
        int length=content.length();
        string NewContent;
        for(int i=0;i<length;++i)
        {
            if(content[i]=='\r')
                continue;
            if(i&&content[i]=='\n'&&content[i-1]=='\n')
                continue;
            NewContent+=content[i];
        }
        if(NewContent.length()!=length)
            content=NewContent;
    }
};
vector<Passage> Passage::passages;
vector<Passage> attachments;

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

bool FliterCheck(const string& line)
{
    for(const string& keyword:Fliter)
        if(line.find(keyword)!=string::npos)
            return 0;
    return 1;
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
                if(FliterCheck(line))
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
        cerr<<"\nundefined line:"<<line<<'|'<<endl;
        if(ReadLine(fin,line))
            continue;
        fin.close();
        return ;
    }
}

void ReadAttachments(const string& Filename)
{
    ifstream fin(Filename);
    Passage p;
    string line;
    if(!fin.is_open())
    {
        cerr<<"Cannot open file "<<Filename<<endl;
        return ;
    }
    ReadLine(fin,p.title);
    p.title=p.title.substr(4);
    while(ReadLine(fin,line))
    {
        p.content+=line;
        p.content+=string("\n");
    }
    fin.close();
    attachments.push_back(p);
}

void FetchFiles()
{
    string path="./MarkdownFiles/",file;
    ifstream fin("./export/filelist.txt");
    ReadLine(fin,file);
    ReadLine(fin,file);
    while(true)
    {
        cerr<<"Reading "<<file<<" ... ";
        ReadPassages(path+file);
        cerr<<"Done."<<endl;
        ReadLine(fin,file);
        if(file.substr(0,4)=="### ")
            break;
    }
    while(ReadLine(fin,file))
    {
        cerr<<"Reading "<<file<<" ... ";
        ReadAttachments(path+file);
        cerr<<"Done."<<endl;
    }
}

Date GetDateNow()
{
    time_t t=time(nullptr);
    tm* now=localtime(&t);
    Date date;
    date.year=now->tm_year+1900;
    date.month=now->tm_mon+1;
    date.day=now->tm_mday;
    return date;
}

void GenarateIndex(ofstream& fout)
{
    Date prevDate;
    fout<<"## Index\n";
    int count=Passage::passages.size();
    for(int i=0;i<count;++i)
    {
        Date currDate=Passage::passages[i].date;
        if(!IsConstant(currDate,prevDate))
        {
            string buffer=to_string(currDate.year)+" 年 "+to_string(currDate.month)+" 月";
            fout<<"- ["<<buffer<<"](###"<<buffer<<")\n";
        }
        prevDate=currDate;
    }
    count=attachments.size();
    for(int i=0;i<count;++i)
        fout<<"- [附件："<<attachments[i].title<<"](###"<<attachments[i].title<<")\n";
}

void MergeFiles()
{
    cerr<<"Merging files ... ";
    sort(Passage::passages.begin(),Passage::passages.end());
    ofstream fout("./export/release.md");
    Date prevDate;
    GenarateIndex(fout);
    fout<<"## Main Content\n";
    for(auto& p:Passage::passages)
    {
        if(!IsConstant(p.date,prevDate))
            fout<<"### "<<p.date.year<<" 年 "<<p.date.month<<" 月\n";
        fout<<"#### "<<p.title<<"\n";
        fout<<p.content;
        prevDate=p.date;
    }
    fout<<"\n## Attachments\n\n";
    for(auto& p:attachments)
    {
        fout<<"### "<<p.title<<"\n";
        fout<<p.content<<"\n\n";
    }
    Date now=GetDateNow();
    fout<<"\n---\n\n";
    fout<<"<p align=\"right\" style=\"font-family: 'Courier New', monospace; font-size: 20px;\">";
    fout<<"released on "<<now.year<<"."<<now.month<<"."<<now.day<<" </p>\n\n";
    fout.close();
    cerr<<"Done."<<endl;
}

void TransformToPDF()
{
    cerr<<"Transforming to PDF ... ";
    system("pandoc -s -o Release.pdf --pdf-engine=xelatex release.md");
    cerr<<"Done."<<endl;
}

void Initialize()
{
    Fliter.push_back("\\large\\mathbf{返回}");
    Fliter.push_back("---");
}

signed main(int argc, char** argv)
{
    vector<string> args(argv,argv+argc);
    Initialize();
    FetchFiles();
    MergeFiles();
    // TransformToPDF();
    return 0;
}