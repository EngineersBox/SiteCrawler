from bs4 import BeautifulSoup
import requests, requests.exceptions, re, sys, os, subprocess, argparse, asyncio, uuid

class URLState:

    def __init__(self, new_urls=deque([]), processed_urls=set(), local_urls=set(), foreign_urls=set(), broken_urls=set()):
        # a queue of urls to be crawled
        self.new_urls = new_urls
        # a set of urls that we have already crawled
        self.processed_urls = processed_urls
        # a set of domains inside the target website
        self.local_urls = local_urls
        # a set of domains outside the target website
        self.foreign_urls = foreign_urls
        # a set of broken urls
        self.broken_urls = broken_urls

class ICrawlerBase:

    def __init__(self):
        self.url_state = URLState()

    def extractResolveLinks(self, response,  url):
        # extract base url to resolve relative links
        parts = urlsplit(url)
        base = "{0.netloc}".format(parts)
        strip_base = base.replace("www.", "")
        base_url = "{0.scheme}://{0.netloc}".format(parts)
        path = url[:url.rfind('/')+1] if '/' in parts.path else url

        # create a beutiful soup for the html document
        soup = BeautifulSoup(response.text, "lxml")

        for link in soup.find_all('a'):
            # extract link url from the anchor
            anchor = link.attrs["href"] if "href" in link.attrs else ''

            if anchor.startswith('/'):
                local_link = base_url + anchor
                self.url_state.local_urls.add(local_link)
            elif strip_base in anchor:
                self.url_state.local_urls.add(anchor)
            elif not anchor.startswith('http'):
                local_link = path + anchor
                self.url_state.local_urls.add(local_link)
            else:
                self.url_state.foreign_urls.add(anchor)

        for i in self.url_state.local_urls:
            if not i in self.url_state.new_urls and not i in self.url_state.processed_urls:
                self.url_state.new_urls.append(i)
        return self.url_state

    def crawlUrlTask(self, domain):
        # a queue of urls to be crawled
        self.url_state = URLState(deque([domain]))
        # move next url from the queue to the set of processed urls
        url = self.url_state.new_urls.popleft()
        self.url_state.processed_urls.add(url)
        is_broken = False
        # get url's content
        print("Processing %s" % url)
        response = None
        try:
            response = requests.head(url)
        except (requests.exceptions.MissingSchema, requests.exceptions.ConnectionError, requests.exceptions.InvalidURL, requests.exceptions.InvalidSchema):
            # add broken urls to it's own set, then continue
            self.url_state.broken_urls.add(url)
            return self.url_state

        if 'content-type' in response.headers:
            content_type = response.headers['content-type']
            if not 'text/html' in content_type:
                return self.url_state

        try:
            response = requests.get(url)
        except (requests.exceptions.MissingSchema, requests.exceptions.ConnectionError, requests.exceptions.InvalidURL, requests.exceptions.InvalidSchema):
            # add broken urls to it's own set, then continue
            self.url_state.broken_urls.add(url)
            return self.url_state

        # extract base url to resolve relative links
        self.url_state = self.extractResolveLinks(
            self.url_state, response, url)
        return self.url_state

    def reportResults(self, ofile, mute):
        if mute is False:
            if ofile is not None:
                return report_file(ofile, self.url_state.processed_urls, self.url_state.local_urls, self.url_state.foreign_urls, self.url_state.broken_urls)
            else:
                return report(self.url_state.processed_urls, self.url_state.local_urls, self.url_state.foreign_urls, self.url_state.broken_urls)
        else:
            if ofile is not None:
                return mute_report_file(ofile, self.url_state.local_urls)
            else:
                return mute_report(self.url_state.local_urls)

class AsyncCrawler(ICrawlerBase):

    def __init__(self):
        super(self)

    async def crawl(self, domain, ofile, mute, tasks_url_state):
        task_id = str(uuid.uuid4())
        tasks_url_state[task_id] = self.crawlUrlTask(domain)
        next_urls = tasks_url_state[task_id].new_urls
        try:
            results = await asyncio.gather(*(self.crawlUrlTask(next_domain for next_domain in next_urls)))
            for res in results:
                tasks_url_state[str(uuid.uuid4())] = res
        except KeyboardInterrupt:
            super.reportResponse()

class Crawler(ICrawlerBase):

    def __init__(self):
        super(self)

    def crawl(self, domain, ofile, mute):
        # a queue of urls to be crawled
        self.url_state.new_urls = deque([domain])
        try:
            # process urls one by one until we exhaust the queue
            while len(self.url_state.new_urls):
                # move next url from the queue to the set of processed urls
                url = self.url_state.new_urls.popleft()
                res = self.crawlUrlTask(url)
                self.url_state.processed_urls = set(self.url_state.processed_urls.union(res.processed_urls))
                self.url_state.broken_urls = set(self.url_state.processed_urls.union(res.broken_urls))
                self.url_state.new_urls = set(self.url_state.processed_urls.union(res.new_urls))
                self.url_state.foreign_urls = set(self.url_state.processed_urls.union(res.foreign_urls))
                self.url_state.local_urls = set(self.url_state.processed_urls.union(res.local_urls))

            print()
            self.reportResults()
        
        except KeyboardInterrupt:
            self.reportResults()
            sys.exit()

class LimitCrawler(ICrawlerBase):

    def __init__(self, limit):
        super(self)
        self.limit = limit

    def crawlLimitUrlTask(self):
        # move next url from the queue to the set of processed urls
        url = self.url_state.new_urls.popleft()
        self.url_state.processed_urls.add(url)
        # get url's content
        print("Processing %s" % url)
        try:
            response = requests.get(url)
        except (requests.exceptions.MissingSchema, requests.exceptions.ConnectionError, requests.exceptions.InvalidURL, requests.exceptions.InvalidSchema):
            # add broken urls to it's own set, then continue
            self.url_state.broken_urls.add(url)
            return

        # extract base url to resolve relative links
        parts = urlsplit(url)
        base = "{0.netloc}".format(parts)
        strip_base = base.replace("www.", "")
        base_url = "{0.scheme}://{0.netloc}".format(parts)
        path = url[:url.rfind('/')+1] if '/' in parts.path else url

        # create a beutiful soup for the html document
        soup = BeautifulSoup(response.text, "lxml")

        for link in soup.find_all('a'):
            # extract link url from the anchor
            anchor = link.attrs["href"] if "href" in link.attrs else ''
            print(anchor)

            if self.limit in anchor:
                self.url_state.limit_urls.add(anchor)
            else:
                pass

        for i in self.url_state.limit_urls:
            if not i in self.url_state.new_urls and not i in self.url_state.processed_urls:
                self.url_state.new_urls.append(i)

    def reportLimitResults(self, ofile, mute):
        if mute is False:
            if ofile is not None:
                return limit_report_file(limit, ofile, self.url_state.processed_urls, self.url_state.limit_urls, self.url_state.broken_urls)
            else:
                return limit_report(limit, self.url_state.processed_urls, self.url_state.limit_urls, self.url_state.broken_urls)
        else:
            if ofile is not None:
                return limit_mute_report_file(limit, ofile, self.url_state.limit_urls)
            else:
                return limit_mute_report(limit, self.url_state.limit_urls)

    def crawl(self, domain, ofile, mute):
        try:
            # process urls one by one until we exhaust the queue
            while len(self.url_state.new_urls):
                self.crawlLimitUrlTask()

            print()
            self.reportLimitResults(ofile, mute)

        except KeyboardInterrupt:
            sys.exit()


def limit_report_file(limit, ofile, processed_urls, limit_urls, broken_urls):
    with open(ofile, 'w') as f:
        print(
            "--------------------------------------------------------------------", file=f)
        print("All found URLs:", file=f)
        for i in processed_urls:
            print(i, file=f)
        print(
            "--------------------------------------------------------------------", file=f)
        print("All " + limit + "URLs:", file=f)
        for j in limit_urls:
            print(j, file=f)
        print(
            "--------------------------------------------------------------------", file=f)
        print("All broken URL's:", file=f)
        for z in broken_urls:
            print(z, file=f)


def limit_report(limit, processed_urls, limit_urls, broken_urls):
    print("--------------------------------------------------------------------")
    print("All found URLs:")
    for i in processed_urls:
        print(i)
    print("--------------------------------------------------------------------")
    print("All " + limit + " URLs:")
    for j in limit_urls:
        print(j)
    print("--------------------------------------------------------------------")
    print("All broken URL's:")
    for z in broken_urls:
        print(z)


def limit_mute_report_file(limit, ofile, limit_urls):
    with open(ofile, 'w') as f:
        print(
            "--------------------------------------------------------------------", file=f)
        print("All " + limit + " URLs:", file=f)
        for j in limit_urls:
            print(j, file=f)


def limit_mute_report(limit, limit_urls):
    print("--------------------------------------------------------------------")
    print("All " + limit + "URLs:")
    for i in limit_urls:
        print(i)

def report_file(ofile, processed_urls, local_urls, foreign_urls, broken_urls):
    with open(ofile, 'w') as f:
        print(
            "--------------------------------------------------------------------", file=f)
        print("All found URLs:", file=f)
        for i in processed_urls:
            print(i, file=f)
        print(
            "--------------------------------------------------------------------", file=f)
        print("All local URLs:", file=f)
        for j in local_urls:
            print(j, file=f)
        print(
            "--------------------------------------------------------------------", file=f)
        print("All foreign URLs:", file=f)
        for x in foreign_urls:
            print(x, file=f)
        print("--------------------------------------------------------------------", file=f)
        print("All broken URL's:", file=f)
        for z in broken_urls:
            print(z, file=f)


def report(processed_urls, local_urls, foreign_urls, broken_urls):
    print("--------------------------------------------------------------------")
    print("All found URLs:")
    for i in processed_urls:
        print(i)
    print("--------------------------------------------------------------------")
    print("All local URLs:")
    for j in local_urls:
        print(j)
    print("--------------------------------------------------------------------")
    print("All foreign URLs:")
    for x in foreign_urls:
        print(x)
    print("--------------------------------------------------------------------")
    print("All broken URL's:")
    for z in broken_urls:
        print(z)


def mute_report_file(ofile, local_urls):
    with open(ofile, 'w') as f:
        print(
            "--------------------------------------------------------------------", file=f)
        print("All local URLs:", file=f)
        for j in local_urls:
            print(j, file=f)


def mute_report(local_urls):
    print("--------------------------------------------------------------------")
    print("All local URLs:")
    for i in local_urls:
        print(i)


def main(argv):
    # define the program description
    text = 'A Python program that crawls a website and recursively checks links to map all internal and external links. Written by Ahad Sheriff.'
    # initiate the parser with a description
    parser = argparse.ArgumentParser(description=text)
    parser.add_argument('--domain', '-d', required=True,
                        help='domain name of website you want to map. i.e. "https://scrapethissite.com"')
    parser.add_argument('--ofile', '-o',
                        help='define output file to save results of stdout. i.e. "test.txt"')
    parser.add_argument('--limit', '-l',
                        help='limit search to the given domain instead of the domain derived from the URL. i.e: "github.com"')
    parser.add_argument('--mute', '-m', action="store_true",
                        help='output only the URLs of pages within the domain that are not broken')
    parser.add_argument('--asynchronous', 'a',
                        help='run crawler asynchronously at each link')
    parser.parse_args()

    # read arguments from the command line
    args = parser.parse_args()

    domain = args.domain
    ofile = args.ofile
    limit = args.limit
    mute = args.mute
    asynchronous = args.asynchronous
    if domain:
        print("domain:", domain)
    if ofile:
        print("output file:", ofile)
    if limit:
        print("limit:", limit)
    if mute:
        print("mute:", mute)
    if asynchronous:
        print("asyncrhonous:", asynchronous)

    if limit is None:
        print()
        if asynchronous is None:
            crawler = Crawler()
            crawler.crawl(domain, ofile, mute)
        else:
            crawler = AsyncCrawler()
            crawler.crawl(domain, ofile, mute)
        print()
    else:
        print()
        crawler = LimitCrawler()
        crawler.crawl(domain, ofile, limit, mute)
        print()


if __name__ == "__main__":
    main(sys.argv[1:])
