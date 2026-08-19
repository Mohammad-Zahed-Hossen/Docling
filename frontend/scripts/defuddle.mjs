import { Defuddle } from "defuddle/node";
import { parseHTML } from "linkedom";

let input = "";
for await (const chunk of process.stdin) input += chunk;

try {
  const request = JSON.parse(input);
  const { document } = parseHTML(request.html);
  const result = await Defuddle(document, request.url, {
    markdown: true,
    removeImages: request.images === "ignore",
    removeSmallImages: true,
    useAsync: false,
  });
  process.stdout.write(JSON.stringify({
    content: result.content,
    title: result.title,
    author: result.author,
    published: result.published,
  }));
} catch {
  process.exitCode = 1;
}
